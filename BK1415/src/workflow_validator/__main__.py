"""Entry point for running workflow validator as a module."""

from workflow_validator.cli.main import main
import sys

if __name__ == '__main__':
    sys.exit(main())