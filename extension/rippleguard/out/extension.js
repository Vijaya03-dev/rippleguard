"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
// ─── Constants ──────────────────────────────────────────────────────────
const FILE_API_URL = 'http://127.0.0.1:8000/api/analyze/';
const FUNCTION_API_URL = 'http://127.0.0.1:8000/api/analyze-function/';
// Map from snake_case reason codes produced by the engine to readable
// labels the user can skim in the webview.
const REASON_CODE_LABELS = {
    'direct_import': 'direct import',
    'high_cochange_frequency': 'high co-change frequency',
    'indirect_relationship': 'indirect relationship',
};
// ─── On-save state ──────────────────────────────────────────────────────
// Tracks the content of each JS/TS file as of the last successful save
// analysis. The first time a file is saved we have no "old" version to
// diff against, so we just cache the content silently and wait for the
// next save.
const lastSavedContent = new Map();
/**
 * activate() is called by VS Code the very first time a user triggers any
 * command registered by this extension (see "contributes.commands" in
 * package.json), OR when a JS/TS file is opened (see "activationEvents"
 * in package.json). It runs once per session and is where we set up all
 * command handlers and event listeners.
 */
function activate(context) {
    console.log('RippleGuard extension activated.');
    // ─── Manual command: file-level analysis (Webview) ──────────────
    // Unchanged from Phase 8. Triggered via Ctrl+Shift+P > "RippleGuard: Analyze Impact".
    const analyzeCmd = vscode.commands.registerCommand('rippleguard.analyze', async () => {
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showErrorMessage('RippleGuard: No active file. Open a file in the editor first.');
            return;
        }
        const changedFile = activeEditor.document.uri.fsPath;
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('RippleGuard: No workspace folder open. Use File > Open Folder first.');
            return;
        }
        const repoPath = workspaceFolders[0].uri.fsPath;
        const panel = vscode.window.createWebviewPanel('rippleguardPanel', 'RippleGuard', vscode.ViewColumn.One, {});
        panel.webview.html = getWebviewContent({
            state: 'loading',
            changedFile: changedFile,
        });
        try {
            const response = await fetch(FILE_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_path: repoPath,
                    changed_file: changedFile,
                }),
            });
            const body = await response.json();
            if (!response.ok) {
                const errorMsg = ('error' in body) ? body.error : `HTTP ${response.status}`;
                panel.webview.html = getWebviewContent({
                    state: 'error',
                    changedFile: changedFile,
                    errorMessage: errorMsg,
                });
                return;
            }
            const result = body;
            panel.webview.html = getWebviewContent({
                state: 'success',
                changedFile: changedFile,
                result: result,
            });
        }
        catch (err) {
            const message = (err instanceof Error) ? err.message : String(err);
            panel.webview.html = getWebviewContent({
                state: 'error',
                changedFile: changedFile,
                errorMessage: `Could not reach the RippleGuard API at ${FILE_API_URL}. ` +
                    `Is the Django server running?\n\nDetails: ${message}`,
            });
        }
    });
    context.subscriptions.push(analyzeCmd);
    // ─── Automatic on-save: function-level analysis (notification) ──
    //
    // WHY notifications instead of a Webview panel:
    //   This fires on every save — opening a full Webview tab each time
    //   would be massively disruptive.  A small, transient notification
    //   in the bottom-right corner is the appropriate UX for automatic,
    //   frequent, background feedback.  The user glances at it and
    //   continues working; it auto-dismisses after a few seconds.
    //
    // WHY failures are silent (console.log only, no error popup):
    //   Unlike the manual command (where the user deliberately asked
    //   for analysis and expects a result or a clear error), this fires
    //   automatically on every save.  If the Django server is down, an
    //   error popup on every Ctrl+S would be far more annoying than the
    //   original problem.  We log to the Debug Console so it's still
    //   diagnosable when needed, but never interrupt the user's flow.
    const onSaveListener = vscode.workspace.onDidSaveTextDocument(async (document) => {
        // Only analyze JS/TS files — skip everything else.
        if (document.languageId !== 'javascript' && document.languageId !== 'typescript') {
            return;
        }
        const filePath = document.uri.fsPath;
        const newContent = document.getText();
        // First save of this file in the session: cache it and skip.
        // We have no "old" version to diff against yet.
        const oldContent = lastSavedContent.get(filePath);
        if (oldContent === undefined) {
            lastSavedContent.set(filePath, newContent);
            console.log(`RippleGuard: First save of ${path.basename(filePath)}, cached for future diffs.`);
            return;
        }
        // Content unchanged — no point calling the API.
        if (oldContent === newContent) {
            return;
        }
        // Get workspace folder for repo_path.
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            console.log('RippleGuard on-save: No workspace folder open, skipping analysis.');
            return;
        }
        const repoPath = workspaceFolders[0].uri.fsPath;
        try {
            const response = await fetch(FUNCTION_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_path: repoPath,
                    filepath: filePath,
                    old_content: oldContent,
                    new_content: newContent,
                }),
            });
            const body = await response.json();
            if (!response.ok) {
                const errorMsg = ('error' in body) ? body.error : `HTTP ${response.status}`;
                console.log(`RippleGuard on-save: API returned error: ${errorMsg}`);
                // Update cache regardless so next save diffs correctly.
                lastSavedContent.set(filePath, newContent);
                return;
            }
            const result = body;
            // Only show a notification if there are actual affected functions.
            // Don't spam the user when nothing is impacted.
            if (result.changed_functions.length > 0 && result.affected_functions.length > 0) {
                const changedNames = result.changed_functions
                    .map(name => `${name}()`)
                    .join(', ');
                const affectedNames = result.affected_functions
                    .map(af => `${af.function_name}()`)
                    .join(', ');
                vscode.window.showInformationMessage(`RippleGuard: Changing ${changedNames} may affect: ${affectedNames}`);
            }
        }
        catch (err) {
            // Silent failure — log only, never show an error popup on
            // automatic saves. See the WHY comment above.
            const message = (err instanceof Error) ? err.message : String(err);
            console.log(`RippleGuard on-save: API unreachable — ${message}`);
        }
        // Always update the cache after analysis (success or failure)
        // so the next save diffs against the correct baseline.
        lastSavedContent.set(filePath, newContent);
    });
    context.subscriptions.push(onSaveListener);
}
function getWebviewContent(data) {
    let bodyHtml;
    switch (data.state) {
        case 'loading':
            bodyHtml = `
				<h1>RippleGuard</h1>
				<p>Analyzing impact of: <strong>${escapeHtml(path.basename(data.changedFile))}</strong></p>
				<p><em>Contacting API…</em></p>`;
            break;
        case 'error':
            bodyHtml = `
				<h1>RippleGuard — Error</h1>
				<p>File: <strong>${escapeHtml(path.basename(data.changedFile))}</strong></p>
				<p style="color: #e74c3c; white-space: pre-wrap;">${escapeHtml(data.errorMessage)}</p>`;
            break;
        case 'success': {
            const affected = data.result.affected_files;
            if (affected.length === 0) {
                bodyHtml = `
					<h1>RippleGuard</h1>
					<p>File: <strong>${escapeHtml(path.basename(data.changedFile))}</strong></p>
					<p>No files are significantly affected by this change.</p>`;
            }
            else {
                const listItems = affected.map(f => {
                    const filename = path.basename(f.affected_file);
                    const reasons = f.severity_reason_codes
                        .map(code => REASON_CODE_LABELS[code] ?? code.replace(/_/g, ' '))
                        .join(', ');
                    return `<li>
						<strong>${escapeHtml(filename)}</strong>
						— severity: ${f.severity_score.toFixed(2)}
						— reasons: ${escapeHtml(reasons)}
					</li>`;
                }).join('\n');
                bodyHtml = `
					<h1>RippleGuard</h1>
					<p>Impact analysis for: <strong>${escapeHtml(path.basename(data.changedFile))}</strong></p>
					<p>${affected.length} file(s) may be affected:</p>
					<ul>${listItems}</ul>`;
            }
            break;
        }
    }
    return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>RippleGuard</title>
</head>
<body>
	${bodyHtml}
</body>
</html>`;
}
function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
/** Called when the extension is deactivated. Nothing to clean up. */
function deactivate() { }
//# sourceMappingURL=extension.js.map