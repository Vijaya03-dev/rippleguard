import * as vscode from 'vscode';

/**
 * activate() is called by VS Code the very first time a user triggers any
 * command registered by this extension (see "contributes.commands" in
 * package.json). It runs once per session and is where we set up all
 * command handlers and long-lived resources.
 *
 * The `context` object holds the extension's lifecycle — anything pushed
 * into `context.subscriptions` will be automatically cleaned up when the
 * extension is deactivated (e.g. when VS Code shuts down).
 */
export function activate(context: vscode.ExtensionContext) {
	console.log('RippleGuard extension activated.');

	// Register the "RippleGuard: Analyze Impact" command.
	// The command ID here ('rippleguard.analyze') must exactly match the
	// "command" field in package.json's contributes.commands — if they
	// don't match, the command will appear in the palette but do nothing
	// (a common and confusing failure mode).
	const analyzeCmd = vscode.commands.registerCommand('rippleguard.analyze', () => {

		// createWebviewPanel() opens a new tab inside VS Code with a
		// fully controllable HTML surface (a "webview").
		//
		// Arguments:
		//   1. viewType: an internal ID for this panel type (used if VS Code
		//      needs to serialize/restore it — can be any unique string).
		//   2. title: what appears on the tab header.
		//   3. showOptions: which editor column to open in.
		//      ViewColumn.One = the main/first editor column.
		const panel = vscode.window.createWebviewPanel(
			'rippleguardPanel',      // viewType
			'RippleGuard',           // title shown on the tab
			vscode.ViewColumn.One,   // open in the primary editor column
			{}                       // webview options (empty for now)
		);

		// Set the HTML content of the webview. In this phase, it's a
		// hardcoded string just to prove the panel renders. Phase 8 will
		// replace this with real UI that displays analysis results.
		panel.webview.html = getWebviewContent();
	});

	context.subscriptions.push(analyzeCmd);
}

/**
 * Returns the full HTML string for the webview panel.
 * Extracted into its own function so it's easy to replace in Phase 8
 * without touching the command registration boilerplate.
 */
function getWebviewContent(): string {
	return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>RippleGuard</title>
</head>
<body>
	<h1>RippleGuard is working</h1>
</body>
</html>`;
}

/**
 * deactivate() is called when the extension is unloaded (VS Code shutdown,
 * extension disabled, etc.). Nothing to clean up in this phase — anything
 * in context.subscriptions is disposed automatically.
 */
export function deactivate() {}
