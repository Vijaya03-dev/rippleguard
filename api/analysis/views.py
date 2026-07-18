import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from engine.analyzer import analyze_change
from engine.function_analyzer import analyze_function_change


class AnalyzeChangeView(APIView):
    """
    POST /api/analyze/

    Accepts { "repo_path": "...", "changed_file": "..." } and returns
    a severity-ranked list of files likely to be affected by the change.

    This is a thin HTTP wrapper around the existing engine — all business
    logic lives in engine/analyzer.py.
    """

    def post(self, request):
        repo_path = request.data.get("repo_path")
        changed_file = request.data.get("changed_file")

        # --- Validate required fields ---
        missing = []
        if not repo_path:
            missing.append("repo_path")
        if not changed_file:
            missing.append("changed_file")
        if missing:
            return Response(
                {"error": f"Missing required field(s): {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Normalize paths to OS-native format so they match graph_builder's
        # node keys (which use os.path.join → backslashes on Windows).
        # Without this, "D:/foo/bar.js" != "D:\\foo\\bar.js" and the
        # changed_file would silently fail to match any graph node.
        repo_path = os.path.normpath(repo_path)
        changed_file = os.path.normpath(changed_file)

        # --- Call the engine ---
        try:
            result = analyze_change(repo_path, changed_file)
        except FileNotFoundError as e:
            return Response(
                {"error": f"Path not found: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": f"Analysis failed: {type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


class AnalyzeFunctionChangeView(APIView):
    """
    POST /api/analyze-function/

    Accepts { "repo_path", "filepath", "old_content", "new_content" } and
    returns function-level impact analysis: which specific functions changed,
    and which functions across the codebase call those changed functions.

    This is a thin HTTP wrapper around engine/function_analyzer.py.
    """

    def post(self, request):
        repo_path = request.data.get("repo_path")
        filepath = request.data.get("filepath")
        old_content = request.data.get("old_content")
        new_content = request.data.get("new_content")

        # --- Validate required fields ---
        missing = []
        if not repo_path:
            missing.append("repo_path")
        if not filepath:
            missing.append("filepath")
        if old_content is None:
            missing.append("old_content")
        if new_content is None:
            missing.append("new_content")
        if missing:
            return Response(
                {"error": f"Missing required field(s): {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Normalize paths for OS-native consistency.
        repo_path = os.path.normpath(repo_path)
        filepath = os.path.normpath(filepath)

        # --- Call the engine ---
        try:
            result = analyze_function_change(
                repo_path, filepath, old_content, new_content
            )
        except FileNotFoundError as e:
            return Response(
                {"error": f"Path not found: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": f"Function analysis failed: {type(e).__name__}: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)

