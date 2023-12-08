#!/usr/bin/env python3

import os, shutil
import argparse
import yaml
import pickle

class LitManReference:
    def __init__(self, config=None):
        self.category = "" if not config or 'category' not in config else config.category
        self.title = "" if not config or 'title' not in config else config.title
        self.authors = [""] if not config or 'authors' not in config else config.authors
        self.year = -1 if not config or 'year' not in config else config.year
        self.file = "" if not config or 'file' not in config else os.path.abspath(config.file)
        self.tags = [""] if not config or 'tags' not in config else config.tags

    def InitData(self):
        self.original_file = ""
        self.notes = []
        self.important = False
        self.printed = False
        self.to_read = True
        self.references = []
        self.citations = []

class LitManArticle(LitManReference):
    def __init__(self, config=None):
        LitManReference.__init__(self, config)
        self.journal = "" if not config or 'journal' not in config else config.journal
        self.issue = -1 if not config or 'issue' not in config else config.issue
        self.number = "" if not config or 'number' not in config else config.number
        if config is not None:
            journal_strip = self.journal.replace(' ', '').replace('.', '')
            self.label = journal_strip+'_'+str(self.issue)+'_'+self.number+'_'+str(self.year)

class LitManConference(LitManReference):
    def __init__(self, config=None):
        LitManReference.__init__(self, config)
        self.conference = "" if not config or 'conference' not in config else config.conference
        self.location = "" if not config or 'location' not in config else config.location
        self.number = -1 if not config or 'number' not in config else config.number
        if config is not None:
            conference_strip = self.conference.replace(' ', '').replace('.', '')
            self.label = conference_strip+'_'+str(self.number)+'_'+str(self.year)

class LitManThesis(LitManReference):
    def __init__(self, config=None):
        LitManReference.__init__(self, config)
        self.university = "" if not config or 'university' not in config else config.university
        self.department = "" if not config or 'department' not in config else config.department
        if config is not None:
            author_strip = self.authors[0].strip().split()[1]
            university_strip = self.university.replace(' ', '').replace('.', '')
            self.label = author_strip+'_'+university_strip+'_'+str(self.year)

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

        # Make reference object
        match config.type:
            case "article":
                new_ref = LitManArticle(config)
            case "conference":
                new_ref = LitManConference(config)
            case "thesis":
                new_ref = LitManThesis(config)
        new_ref.InitData()
        new_ref.tags += [new_ref.category.lower()]

        # Copy file
        copy_path = '{}/{}'.format(self.LitManFiles, config.category.lower())
        if not os.path.exists(copy_path):
            os.mkdir(copy_path)
        extension = os.path.splitext(os.path.basename(config.file))[1]
        copy_file = '{}/{}'.format(copy_path, new_ref.label+extension)
        shutil.copy(config.file, copy_file)
        new_ref.original_file = config.file
        new_ref.file = copy_file

        # Add to database
        with open(self.LitManDB, 'a') as outfile:
            yaml.dump(dict({new_ref.label: vars(new_ref)}), outfile, default_flow_style=False, allow_unicode=True)
        self.Cache()

    def Cache(self):
        with open(self.LitManDB, 'r') as litman_db_file:
            litman_db = yaml.safe_load(litman_db_file)
            with open(self.LitManCache, 'wb') as litman_pickle_file:
                pickle.dump(litman_db, litman_pickle_file, protocol=pickle.HIGHEST_PROTOCOL)

    def Edit(self, config):
        # Get the database
        litman_db = self.LoadDB(config)

        # Find the requested reference
        if config.ref not in litman_db:
            raise ValueError("Requested reference {} not in database.".format(config.ref))
        ref = litman_db[config.ref]

        # Make edits
        if config.add_tag is not None:
            ref["tags"].append(config.add_tag)
        if config.rm_tag is not None:
            ref["tags"].remove(config.rm_tag)
        if config.rm_note is not None:
            del ref["notes"][config.rm_note]

        self.Resave(litman_db)

    def Link(self, config):
        # Get the database
        litman_db = self.LoadDB(config)

        # Find the requested reference
        if config.ref not in litman_db:
            raise ValueError("Requested reference {} not in database.".format(config.ref))
        ref = litman_db[config.ref]

        # Find the citated reference
        if config.cite not in litman_db:
            raise ValueError("Requested reference {} not in database.".format(config.cite))
        cite = litman_db[config.cite]

        # Link!
        ref["references"].append(config.cite)
        cite["citations"].append(config.ref)
        
        self.Resave(litman_db)

    def List(self, config):
        litman_db = self.LoadDB(config)
        entries = self.Winnow(litman_db, config)
        self.Print(litman_db, entries, config)

    def LoadDB(self, config):
        if config.no_cache:
            with open(self.LitManDB, 'r') as litman_db_file:
                litman_db = yaml.safe_load(litman_db_file)
        else:
            with open(self.LitManCache, 'rb') as litman_pickle_file:
                litman_db = pickle.load(litman_pickle_file)
        return litman_db

    def Mark(self, config):
        # Find the requested reference
        litman_db = self.LoadDB(config)
        if config.ref not in litman_db:
            raise ValueError("Requested reference {} not in database.".format(config.ref))
        ref = litman_db[config.ref]

        if config.important is not None and config.important:
            ref["important"] = True
        if config.printed is not None and config.printed:
            ref["printed"] = True
        if config.to_read is not None and config.to_read:
            ref["to_read"] = True

        self.Resave(litman_db)

    def Note(self, config):
        # Find the requested reference
        litman_db = self.LoadDB(config)
        if config.ref not in litman_db:
            raise ValueError("Requested reference {} not in database.".format(config.ref))
        ref = litman_db[config.ref]

        # Add notes
        for note in config.note:
            ref['notes'].append(note)

        self.Resave(litman_db)

    def Open(self, config):
        # Get the requested entries
        litman_db = self.LoadDB(config)
        entries = self.Winnow(litman_db, config)
        if not len(entries):
            print("\nNo entries found.\n")
        if config.all:
            file_list = " ".join([e['file'] for e in entries])
        else:
            file_list = entries[0]['file']
        os.system("open {}".format(file_list))

    def Print(self, litman_db, entries, config):
        # This flashes because I got carried away with the ANSI formatting
        print("\033[1;5m\nMatching entries:\033[0m\n")

        # Print each selected entry
        for entry in entries:

            # Basic information
            print("{}:{}{}{}{}\n  {}\n    {}\n    {} {} {} ({})"
                  .format('\033[34m{}\033[30m'.format(entry['label']),
                          " \033[7mImportant\033[0m" if entry["important"] else "",
                          " \033[7mPrinted\033[0m" if entry["printed"] else "",
                          " \033[7mTo Read\033[0m" if entry["to_read"] else "",
                          " \033[7mNotes\033[0m" if entry["notes"] else "",
                          '\033[4m{}\033[0m'.format(entry['title']),
                          '\033[3m{}\033[0m'.format(', '.join(entry['authors'])),
                          entry['journal'],
                          '\033[1m{}\033[0m'.format(entry['issue']),
                          entry['number'],
                          entry['year']))

            # Tags and notes
            if not config.compact:
                print("  (\033[31m{}\033[30m)".format(' '.join(entry['tags'])))
                for note in entry['notes']:
                    print("\033[2m    - {}\033[0m".format(note))

            # Links
            if config.links:
                print("  \033[32mCitations:\033[0m")
                for citation in entry['citations']:
                    cite = litman_db[citation]
                    print("    - {}: {}".format(cite['label'], cite['title']))
                print("  \033[32mReferences:\033[0m")
                for reference in entry['references']:
                    ref = litman_db[reference]
                    print("    - {}: {}".format(ref['label'], ref['title']))

            print()

    def Resave(self, litman_db):
        with open(self.LitManDB, 'w') as outfile:
            yaml.dump(litman_db, outfile, default_flow_style=False, allow_unicode=True)
        self.Cache()

    def Winnow(self, litman_db, config):
        # Return all entries by default
        entries = list(litman_db.values())

        # Reference
        if config.ref is not None:
            entries = []
            for ref in config.ref:
                if ref not in litman_db:
                    raise ValueError("Requested entry {} not in database.".format(config.label))
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

        # Markers
        if 'important' in config and config.important:
            keep = []
            for i_entry,entry in enumerate(entries):
                if entry['important']:
                    keep.append(i_entry)
            entries = [e for i,e in enumerate(entries) if i in keep]
        if 'to_read' in config and config.to_read:
            keep = []
            for i_entry,entry in enumerate(entries):
                if entry['to_read']:
                    keep.append(i_entry)
            entries = [e for i,e in enumerate(entries) if i in keep]

        return entries

def ParseArguments():

    parser = argparse.ArgumentParser(prog="litman",
                                     description="Literature Manager: Managing literature for the lit man.")
    parser.add_argument("--no_cache", action='store_true',
                        help="Force load from the YAML file rather than the cache.")
    subparser = parser.add_subparsers(title="litman command", dest="command")
    subparser.required = True

    # Cache
    cache_parser = subparser.add_parser("cache", help="Rebuild the LitMan cache.")

    # Add
    add_parser = subparser.add_parser("add", help="Add reference to LitMan.")
    add_subparser = add_parser.add_subparsers(title="literature type", dest="type")
    add_subparser.required = True

    article_parser = add_subparser.add_parser("article", help="Add article-type reference.")
    article_object = LitManArticle()
    for var in vars(article_object):
        article_parser.add_argument("--{}".format(var), required=True,
                                    type=type(vars(article_object)[var][0]) if type(vars(article_object)[var])==list else type(var),
                                    nargs='+' if type(vars(article_object)[var])==list else '?')

    conference_parser = add_subparser.add_parser("conference", help="Add conference-type reference.")
    conference_object = LitManConference()
    for var in vars(conference_object):
        conference_parser.add_argument("--{}".format(var), required=True,
                                       type=type(vars(conference_object)[var][0]) if type(vars(conference_object)[var])==list else type(var),
                                       nargs='+' if type(vars(conference_object)[var])==list else 1)

    thesis_parser = add_subparser.add_parser("thesis", help="Add thesis-type reference.")
    thesis_object = LitManThesis()
    for var in vars(thesis_object):
        thesis_parser.add_argument("--{}".format(var), required=True,
                                   type=type(vars(thesis_object)[var][0]) if type(vars(thesis_object)[var])==list else type(var),
                                   nargs='+' if type(vars(thesis_object)[var])==list else 1)

    # Edit
    edit_parser = subparser.add_parser("edit", help="Edit existing reference.")
    edit_parser.add_argument("--ref", type=str, required=True,
                             help="LitMan reference.")
    edit_parser.add_argument("--add_tag", type=str,
                             help="Add tag to reference.")
    edit_parser.add_argument("--rm_tag", type=str,
                             help="Remove tag from reference.")
    edit_parser.add_argument("--rm_note", type=int,
                             help="Remove note (by note index, starting from 0) from reference.")

    # Mark
    mark_parser = subparser.add_parser("mark", help="Mark reference with label.")
    mark_parser.add_argument("--ref", type=str, required=True,
                             help="Reference in LitMan to mark.")
    mark_parser.add_argument("--important", action='store_true',
                             help="Mark reference as important.")
    mark_parser.add_argument("--printed", action='store_true',
                             help="Add note to the reference that it has been printed.")
    mark_parser.add_argument("--to_read", action='store_true',
                             help="Mark reference as to-read.")
    mark_parser.add_argument("--read", action='store_true',
                             help="Mark reference as read.")

    # Link
    link_parser = subparser.add_parser("link", help="Link references.")
    link_parser.add_argument("--ref", type=str, required=True,
                             help="Reference in LitMan to add link to.")
    link_parser.add_argument("--cite", type=str, required=True,
                             help="Literature cited by this reference.")

    # List
    list_parser = subparser.add_parser("list", help="List references in LitMan.")
    list_parser.add_argument("--search", type=str, nargs='+',
                             help="Search terms.")
    list_parser.add_argument("--ref", type=str, nargs='+',
                             help="LitMan reference.")
    list_parser.add_argument("--authors", type=str, nargs='+',
                             help="Authors to filter.")
    list_parser.add_argument("--important", action='store_true',
                             help="List only references marked as important.")
    list_parser.add_argument("--to_read", action='store_true',
                             help="List only references marked as to-read.")
    list_parser.add_argument("--compact", action='store_true',
                             help="Print items in a compact view.")
    list_parser.add_argument("--links", action='store_true',
                             help="Print links for each item.")

    # Open
    open_parser = subparser.add_parser("open", help="Open file for reference in LitMan.")
    open_parser.add_argument("--search", type=str, nargs='+',
                             help="Search terms.")
    open_parser.add_argument("--ref", type=str, nargs='+',
                             help="LitMan reference.")
    open_parser.add_argument("--all", action='store_true',
                             help="Open all matching entries.")

    # Note
    note_parser = subparser.add_parser("note", help="Add note to existing reference.")
    note_parser.add_argument("--ref", type=str, required=True,
                             help="LitMan reference.")
    note_parser.add_argument("--note", type=str, nargs='+', required=True,
                             help="Add note to reference; multiple entries can be made in bullet-point style.")

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
        case "edit":
            litman.Edit(config)
        case "mark":
            litman.Mark(config)
        case "link":
            litman.Link(config)
        case "list":
            litman.List(config)
        case "open":
            litman.Open(config)
        case "note":
            litman.Note(config)

if __name__ == "__main__":
    main()
