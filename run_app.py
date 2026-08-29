import os, sys, webbrowser, time
import uvicorn

if __name__ == "__main__":
    print("="*58)
    print("  XiVLM-Loop v2.0 Industrial Quality Inspection Console")
    print("  Starting server at http://localhost:8000 ...")
    print("="*58)
    webbrowser.open("http://localhost:8000")
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=False)
