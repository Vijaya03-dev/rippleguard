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
const API_URL = 'http://127.0.0.1:8000/api/analyze/';
// Map from snake_case reason codes produced by the engine to readable
// labels the user can skim in the webview.
const REASON_CODE_LABELS = {
    'direct_import': 'direct import',
    'high_cochange_frequency': 'high co-change frequency',
    'indirect_relationship': 'indirect relationship',
};
/**
 * activate() is called by VS Code the very first time a user triggers any
 * command registered by this extension (see "contributes.commands" in
 * package.json). It runs once per session and is where we set up all
 * command handlers.
 */
function activate(context) {
    console.log('RippleGuard extension activated.');
    const analyzeCmd = vscode.commands.registerCommand('rippleguard.analyze', async () => {
        // --- 1. Get the active file path ---
        // vscode.window.activeTextEditor is undefined if no editor tab is
        // focused (e.g. the user has the terminal or settings tab open).
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showErrorMessage('RippleGuard: No active file. Open a file in the editor first.');
            return;
        }
        const changedFile = activeEditor.document.uri.fsPath;
        // --- 2. Get the workspace folder path (used as repo_path) ---
        // workspaceFolders is undefined when VS Code is opened with no
        // folder — just a loose file. The API needs a directory to scan.
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('RippleGuard: No workspace folder open. Use File > Open Folder first.');
            return;
        }
        const repoPath = workspaceFolders[0].uri.fsPath;
        // --- 3. Open the webview panel immediately with a loading state ---
        // We show "Analyzing…" right away so the user knows the extension
        // is working, then update the HTML once the API responds.
        const panel = vscode.window.createWebviewPanel('rippleguardPanel', 'RippleGuard', vscode.ViewColumn.One, {});
        panel.webview.html = getWebviewContent({
            state: 'loading',
            changedFile: changedFile,
        });
        // --- 4. Call the Django API ---
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_path: repoPath,
                    changed_file: changedFile,
                }),
            });
            // The API returns JSON in all cases (200, 400, 500).
            const body = await response.json();
            if (!response.ok) {
                // Non-2xx: the API returned an error object { error: "..." }.
                const errorMsg = ('error' in body) ? body.error : `HTTP ${response.status}`;
                panel.webview.html = getWebviewContent({
                    state: 'error',
                    changedFile: changedFile,
                    errorMessage: errorMsg,
                });
                return;
            }
            // --- 5. Success: render the results ---
            const result = body;
            panel.webview.html = getWebviewContent({
                state: 'success',
                changedFile: changedFile,
                result: result,
            });
        }
        catch (err) {
            // --- 6. Network-level failure (server not running, DNS, etc.) ---
            const message = (err instanceof Error) ? err.message : String(err);
            panel.webview.html = getWebviewContent({
                state: 'error',
                changedFile: changedFile,
                errorMessage: `Could not reach the RippleGuard API at ${API_URL}. ` +
                    `Is the Django server running?\n\nDetails: ${message}`,
            });
        }
    });
    context.subscriptions.push(analyzeCmd);
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
                    // Convert the affected_file absolute path to just the filename.
                    const filename = path.basename(f.affected_file);
                    // Convert snake_case reason codes to readable labels.
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
/**
 * Minimal HTML escaping to prevent accidental injection of file paths
 * or error messages that contain angle brackets, ampersands, or quotes.
 */
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