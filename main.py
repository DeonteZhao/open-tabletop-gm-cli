import sys
import argparse
from config import interactive_config
from campaign import create_campaign, list_campaigns
from cli import load_campaign
from importer import import_pdf

def main():
    parser = argparse.ArgumentParser(description="Open Tabletop GM CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # config
    subparsers.add_parser("config", help="Run interactive configuration")

    # new
    new_parser = subparsers.add_parser("new", help="Create a new campaign")
    new_parser.add_argument("name", type=str, help="Name of the campaign")

    # list
    subparsers.add_parser("list", help="List all campaigns")

    # load
    load_parser = subparsers.add_parser("load", help="Load a campaign and start playing")
    load_parser.add_argument("name", type=str, help="Name of the campaign")

    # import
    import_parser = subparsers.add_parser("import", help="Import a PDF into a campaign")
    import_parser.add_argument("name", type=str, help="Name of the campaign")
    import_parser.add_argument("pdf_path", type=str, help="Path to the PDF file")

    args = parser.parse_args()

    if args.command == "config":
        interactive_config()
    elif args.command == "new":
        create_campaign(args.name)
    elif args.command == "list":
        list_campaigns()
    elif args.command == "load":
        load_campaign(args.name)
    elif args.command == "import":
        import_pdf(args.name, args.pdf_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
