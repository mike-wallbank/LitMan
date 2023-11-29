#!/usr/bin/env python3

import os, shutil
import argparse
import yaml
import pickle

class LitMan:
    def __init__(self, directory):
        self.LitManDir = directory
        self.LitManDB = directory+'/litman.yaml'
        if not os.path.exists(self.LitManDB):
            os.system('touch {}'.format(self.LitManDB))
        self.LitManFiles = directory+'/files/'
        if not os.path.exists(self.LitManFiles):
            os.mkdir(self.LitManFiles)
        self.LitManCache = directory+'/litman.pickle'

    def Add(self, config):

        # Define a custom reference format
        journal_strip = config.journal.replace(' ', '').replace('.', '')
        reference = journal_strip+'_'+str(config.issue)+'_'+config.number+'_'+str(config.year)

        # Copy file
        copy_path = '{}/{}'.format(self.LitManFiles, config.category.lower())
        if not os.path.exists(copy_path):
            os.mkdir(copy_path)
        extension = os.path.splitext(os.path.basename(config.file))[1]
        copy_file = '{}/{}'.format(copy_path, reference+extension)
        shutil.copy(config.file, copy_file)

        # Add to database
        new_ref = {
            reference: {
                "title": config.title,
                "authors": config.authors,
                "journal": config.journal,
                "issue": config.issue,
                "number": config.number,
                "year": config.year,
                "file": os.path.abspath(copy_file),
                "original_file": os.path.abspath(config.file),
                "tags": [config.category.lower()] + [t.lower() for t in config.tags],
                "notes": [],
                "reference": reference
            }
        }
        with open(self.LitManDB, 'a') as outfile:
            yaml.dump(new_ref, outfile, default_flow_style=False, allow_unicode=True)
        self.Cache()

    def Cache(self):
        with open(self.LitManDB, 'r') as litman_db_file:
            litman_db = yaml.safe_load(litman_db_file)
            with open(self.LitManCache, 'wb') as litman_pickle_file:
                pickle.dump(litman_db, litman_pickle_file, protocol=pickle.HIGHEST_PROTOCOL)

    def List(self, config):
        entries = self.Winnow(config)
        self.Print(entries, config)

    def LoadDB(self, config):
        if config.no_cache:
            with open(self.LitManDB, 'r') as litman_db_file:
                litman_db = yaml.safe_load(litman_db_file)
        else:
            with open(self.LitManCache, 'rb') as litman_pickle_file:
                litman_db = pickle.load(litman_pickle_file)
        return litman_db

    def Note(self, config):
        # Get the database
        litman_db = self.LoadDB(config)

        # Find the requested reference
        if config.ref not in litman_db:
            raise ValueError("Requested reference {} not in database.".format(config.ref))
        ref = litman_db[config.ref]

        # Add notes
        for note in config.note:
            ref['notes'].append(note)

        # Resave
        with open(self.LitManDB, 'w') as outfile:
            yaml.dump(litman_db, outfile, default_flow_style=False, allow_unicode=True)
        self.Cache()

    def Open(self, config):
        entries = self.Winnow(config)
        if not len(entries):
            print("\nNo entries found.\n")
        if config.all:
            file_list = " ".join([e['file'] for e in entries])
        else:
            file_list = entries[0]['file']
        os.system("open {}".format(file_list))

    def Print(self, entries, config):
        print("\nMatching entries:\n")
        for entry in entries:
            print("{}:\n  {}, {}, {} {} {} ({})"
                  .format(entry['reference'], entry['title'], entry['authors'], entry['journal'], entry['issue'], entry['number'], entry['year']))
            if config.notes:
                for note in entry['notes']:
                    print("    - {}".format(note))
            print()

    def Winnow(self, config):

        # Get the database
        litman_db = self.LoadDB(config)

        # Return all entries by default
        entries = list(litman_db.values())

        # Reference
        if config.ref is not None:
            entries = []
            for ref in config.ref:
                if ref not in litman_db:
                    raise ValueError("Requested entry {} not in database.".format(config.reference))
                entries.append(litman_db[ref])

        # Search
        if config.search is not None:
            remove = []
            for i_entry,entry in enumerate(entries):
                for term in config.search:
                    if term.lower() in entry['title'].lower() or \
                       term.lower() in [t.lower() for t in entry['tags']] or \
                       term.lower() in ' '.join([a.lower() for a in entry['authors']]) or \
                       term in str(entry['year']):
                        pass
                    else:
                        remove.append(i_entry)
            entries = [e for i,e in enumerate(entries) if i not in remove]

        # Authors
        if 'authors' in config and config.authors is not None:
            remove = []
            for i_entry,entry in enumerate(entries):
                for author in config.authors:
                    if author not in entry['authors']:
                        remove.append(i_entry)
            entries = [e for i,e in enumerate(entries) if i not in remove]

        return entries

def ParseArguments():

    parser = argparse.ArgumentParser(prog="litman",
                                     description="Literature Manager: Managing literature for the lit man.")
    subparser = parser.add_subparsers(title="litman command", dest="command")
    subparser.required = True

    # Cache
    cache_parser = subparser.add_parser("cache", help="Remake the LitMan cache.")

    # Add
    add_parser = subparser.add_parser("add", help="Add reference to LitMan.")
    add_parser.add_argument("--category", type=str, required=True, choices=["accelerator", "neutrino"],
                            help="Paper category.")
    add_parser.add_argument("--title", type=str, required=True,
                            help="Title.")
    add_parser.add_argument("--authors", type=str, nargs='+', required=True,
                            help="Authors.")
    add_parser.add_argument("--journal", type=str, required=True,
                            help="Journal.")
    add_parser.add_argument("--issue", type=int, required=True,
                            help="Journal issue.")
    add_parser.add_argument("--number", type=str, required=True,
                            help="Article number.")
    add_parser.add_argument("--year", type=int, required=True,
                            help="Publication year.")
    add_parser.add_argument("--file", type=str, required=True,
                             help="Document file.")
    add_parser.add_argument("--tags", type=str, nargs='+', required=True,
                            help="Tags for organizing and retrieving the reference.")

    # List
    list_parser = subparser.add_parser("list", help="List references in LitMan.")
    list_parser.add_argument("--search", type=str, nargs='+',
                             help="Search terms.")
    list_parser.add_argument("--ref", type=str, nargs='+',
                             help="LitMan reference.")
    list_parser.add_argument("--authors", type=str, nargs='+',
                             help="Authors to filter.")
    list_parser.add_argument("--notes", action='store_true',
                             help="Print notes for each item.")
    list_parser.add_argument("--links", action='store_true',
                             help="Print links for each item.")
    list_parser.add_argument("--no_cache", action='store_true',
                             help="Force load from the YAML file rather than the cache.")

    # Open
    open_parser = subparser.add_parser("open", help="Open file for reference in LitMan.")
    open_parser.add_argument("--search", type=str, nargs='+',
                             help="Search terms.")
    open_parser.add_argument("--ref", type=str, nargs='+',
                             help="LitMan reference.")
    open_parser.add_argument("--all", action='store_true',
                             help="Open all matching entries.")
    open_parser.add_argument("--no_cache", action='store_true',
                             help="Force load from the YAML file rather than the cache.")

    # Note
    note_parser = subparser.add_parser("note", help="Add note to existing reference.")
    note_parser.add_argument("--ref", type=str, required=True,
                             help="LitMan reference.")
    note_parser.add_argument("--note", type=str, nargs='+', required=True,
                             help="Add note to reference; multiple entries can be made in bullet-point style.")
    note_parser.add_argument("--no_cache", action='store_true',
                             help="Force load from the YAML file rather than the cache.")

    return parser.parse_args()

def main():

    # Parse arguments
    config = ParseArguments()

    # Set up database
    with open("{}/.litman".format(os.path.expanduser("~")), 'r') as litman_config_file:
        litman_config = yaml.safe_load(litman_config_file)
    if 'directory' not in litman_config:
        raise RunTimeError("LitMan directory required.")
    litman = LitMan(litman_config['directory'].replace('~', os.path.expanduser("~")))

    # Do stuff
    match config.command:
        case "cache":
            litman.Cache()
        case "add":
            litman.Add(config)
        case "list":
            litman.List(config)
        case "open":
            litman.Open(config)
        case "note":
            litman.Note(config)

if __name__ == "__main__":
    main()
