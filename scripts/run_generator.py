"""Launcher for the UI Claims Generator on Databricks.

Adds the scripts directory to sys.path so the generator package
can use absolute imports when executed via spark_python_task.
"""
import os
import sys

scripts_dir = "/Workspace/Users/thomas.seufert@databricks.com/scripts"
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from generator.main import main

if __name__ == "__main__":
    main()
