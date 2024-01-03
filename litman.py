#!/usr/bin/env python3

import os, shutil
import argparse, yaml
import copy, pickle

# Reference types are defined as class objects.
# Change and add properties by modifying these structures.
# The base class holds the basic information common across
# all reference types.  Each type can implement its own
# specific properties; each type is also required to define
# a label format for bookkeeping and referencing, and an
# output format for printing.

# Base class
class LitManReference:
    def InitRequiredAttributes(self):
        self.category = ""
        self.title = ""
        self.authors = [""]
        self.year = -1
        self.file = ""
        self.tags = [""]
        self.important = False
        self.printed = False
        self.read = False

    def Initialize(self, config):
        self.type = config.type
        self.category = config.category
        self.title = config.title
        self.authors = config.authors
        self.year = config.year
        self.file = os.path.abspath(config.file)
        self.tags = config.tags + [config.category.lower()]
        self.tags.sort()
        self.important = config.important
        self.printed = config.printed
        self.read = config.read
        self.original_file = None
        self.notes = []
        self.references = []
        self.citations = []

    def Strip(self, attribute):
        return attribute.replace(' ', '').replace('.', '').replace(':', '').replace('(', '').replace(')', '')

# Article reference type
class LitManArticle(LitManReference):
    def __init__(self):
        self.InitRequiredAttributes()

    def InitRequiredAttributes(self):
        super().InitRequiredAttributes()
        self.journal = ""
        self.issue = -1
        self.number = ""

    def Initialize(self, config):
        super().Initialize(config)
        self.journal = config.journal
        self.issue = config.issue
        self.number = config.number
        self.Label()

    def Label(self):
        self.label = super().Strip(self.journal)+'_'+str(self.issue)+'_'+self.number+'_'+str(self.year)

    @staticmethod
    def FormatSpecificInfo(article):
        return "{} {} {}".format(article['journal'],
                                 '\033[1m{}\033[0m'.format(article['issue']),
                                 article['number'])


# Conference reference type
class LitManConference(LitManReference):
    def __init__(self):
        self.InitRequiredAttributes()

    def InitRequiredAttributes(self):
        super().InitRequiredAttributes()
        self.conference = ""
        self.location = ""
        self.number = ""

    def Initialize(self, config):
        super().Initialize(config)
        self.conference = config.conference
        self.location = config.location
        self.number = config.number
        self.Label()

    def Label(self):
        self.label = super().Strip(self.conference)+'_'+str(self.number)+'_'+str(self.year)

    @staticmethod
    def FormatSpecificInfo(conference):
        return "{}, {}, {}".format(conference['conference'],
                                   conference['location'],
                                   conference['number'])

# Note reference type
class LitManNote(LitManReference):
    def __init__(self):
        self.InitRequiredAttributes()

    def InitRequiredAttributes(self):
        super().InitRequiredAttributes()
        self.name = ""

    def Initialize(self, config):
        super().Initialize(config)
        self.name = config.name
        self.Label()

    def Label(self):
        self.label = super().Strip(self.name)+'_'+str(self.year)

    @staticmethod
    def FormatSpecificInfo(note):
        return note['name']

# Thesis reference type
class LitManThesis(LitManReference):
    def __init__(self):
        self.InitRequiredAttributes()

    def InitRequiredAttributes(self):
        super().InitRequiredAttributes()
        self.university = ""
        self.department = ""

    def Initialize(self, config):
        super().Initialize(config)
        self.university = config.university
        self.department = config.department
        self.Label()

    def Label(self):
        author_strip = self.authors[0].strip().split()[1]
        self.label = author_strip+'_'+super().Strip(self.university)+'_'+str(self.year)

    @staticmethod
    def FormatSpecificInfo(thesis):
        return "{}, {}".format(thesis['university'], thesis['department'])

# Book reference type
class LitManBook(LitManReference):
    def __init__(self):
        self.InitRequiredAttributes()

    def InitRequiredAttributes(self):
        super().InitRequiredAttributes()
        self.publisher = ""
        self.edition = ""

    def Initialize(self, config):
        super().Initialize(config)
        self.publisher = config.publisher
        self.edition = config.edition
        self.Label()

    def Label(self):
        self.label = super().Strip(self.title)+'_'+self.edition+'Edition_'+super().Strip(self.publisher)

    @staticmethod
    def FormatSpecificInfo(book):
        return "{}, {} Edition".format(book['publisher'], book['edition'])

reference_types = {"article":LitManArticle(),
                   "conference":LitManConference(),
                   "note":LitManNote(),
                   "thesis":LitManThesis(),
                   "book":LitManBook()}

class LitMan:
    def __init__(self, config):

        # Set required paths
        if 'directory' not in config or 'backup' not in config:
            raise RuntimeError("\n\033[31mLitMan directory and backup required (use \033[31;1mlitman setup\033[31m).\033[31m\n")
        self.LitManDir = config['directory']
        if not os.path.exists(self.LitManDir):
            raise RuntimeError("\n\033[31mLitMan directory {} does not exist.\033[0m".format(self.LitManDir))
        self.BackupDir = config['backup']
        if not os.path.exists(self.LitManDir):
            raise RuntimeError("\n\033[31mLitMan directory {} does not exist.\033[0m".format(self.LitManDir))

        # Set database files
        self.LitManDB = self.LitManDir+'/litman.yaml'
        if not os.path.exists(self.LitManDB):
            with open(self.LitManDB, 'w'):
                os.utime(self.LitManDB, None)
        self.LitManFiles = self.LitManDir+'/files/'
        if not os.path.exists(self.LitManFiles):
            os.mkdir(self.LitManFiles)
        self.LitManCache = self.LitManDir+'/litman.pickle'

    def Add(self, config):

        # Make reference object
        new_ref = copy.deepcopy(reference_types[config.type])
        new_ref.Initialize(config)

        # Ensure this is a new entry
        litman_db = self.LoadDB(config)
        if litman_db is not None and new_ref.label in litman_db:
            raise NameError("\033[31mReference \033[34m{}\033[31m already exists in database.\033[0m".format(new_ref.label))

        # Copy file
        copy_path = '{}/{}'.format(self.LitManFiles, config.category.lower())
        if not os.path.exists(copy_path):
            os.mkdir(copy_path)
        extension = os.path.splitext(os.path.basename(config.file))[1]
        copy_file = '{}/{}'.format(copy_path, new_ref.label+extension)
        shutil.copy(config.file, copy_file)
        new_ref.file = copy_file

        # Remove original file
        if not config.keep_original_file:
            os.remove(config.file)
        else:
            new_ref.original_file = config.file

        # Add to database
        with open(self.LitManDB, 'a') as outfile:
            yaml.dump(dict({new_ref.label: vars(new_ref)}), outfile, default_flow_style=False, allow_unicode=True)
        self.Cache()

    def Backup(self):
        with open("{}/.litman".format(os.path.expanduser("~")), 'r') as litman_config_file:
            litman_config = yaml.safe_load(litman_config_file)
        if 'backup' not in litman_config:
            raise RuntimeError("\n\033[31mLitMan backup directory not set (use \033[31;1mlitman setup --backup\033[31m to add)\033[0m.\n")
        backup_directory = litman_config['backup']
        if not os.path.exists(backup_directory):
            raise RuntimeError("\n\033[31mLitMan backup directory {} does not exist.\033[0m\n".format(backup_directory))
        copy_path = backup_directory+'/'+os.path.basename(self.LitManDB)+'.backup'
        shutil.copy(self.LitManDB, copy_path)

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
            raise ValueError("\n\033[31mRequested reference \033[34m{}\033[31m not in database.\033[0m\n".format(config.ref))
        ref = litman_db[config.ref]

        # Make edits
        if config.add_tag is not None:
            ref["tags"].append(config.add_tag)
            ref["tags"].sort()

        if config.rm_tag is not None:
            Confirm("Remove tag {} from {}?".format(config.rm_tag, config.ref))
            ref["tags"].remove(config.rm_tag)

        if config.rm_note is not None:
            Confirm("Remove note {} from {}?".format(config.rm_note, config.ref))
            del ref["notes"][config.rm_note]

        if config.rm_ref is not None:
            cited = litman_db[ref["references"][config.rm_ref]]
            Confirm("Remove reference {} from {} (and citation {} from {})?"
                    .format(cited['label'], config.ref, config.ref, cited['label']))
            ref["references"].remove(cited['label'])
            cited["citations"].remove(config.ref)

        if config.rm_cite is not None:
            refed = litman_db[ref["citations"][config.rm_cite]]
            Confirm("Remove citation {} from {} (and reference {} from {})?"
                    .format(refed['label'], config.ref, config.ref, refed['label']))
            ref['citations'].remove(refed['label'])
            refed['references'].remove(config.ref)

        self.Resave(litman_db)

    def Link(self, config):
        # Get the database
        litman_db = self.LoadDB(config)

        # Find the requested reference
        if config.ref not in litman_db:
            raise ValueError("\n\033[31mRequested reference \033[34m{}\033[31m not in database.\033[0m\n".format(config.ref))
        ref = litman_db[config.ref]

        # Find the citated reference
        if config.cite not in litman_db:
            raise ValueError("\n\033[31mRequested reference \033[34m{}\033[31m not in database.\033[0m\n".format(config.cite))
        cite = litman_db[config.cite]

        # Link!
        ref["references"].append(config.cite)
        cite["citations"].append(config.ref)
        
        self.Resave(litman_db)

    def List(self, config):
        litman_db = self.LoadDB(config)
        entries = self.Winnow(litman_db, config)
        if config.clipboard and len(entries):
            os.system("echo {} | tr -d '\n' | pbcopy".format(entries[0]['label'].strip()))
        self.PrintReferences(litman_db, entries, config)

    def LoadDB(self, config):
        if config.no_cache or not os.path.exists(self.LitManCache):
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
            raise ValueError("\n\033[31mRequested reference \033[34m{}\033[31m not in database.\033[0m\n".format(config.ref))
        ref = litman_db[config.ref]

        # Mark with requested tag
        if config.important is not None and config.important:
            ref["important"] = True
        if config.printed is not None and config.printed:
            ref["printed"] = True
        if config.to_read is not None and config.to_read:
            ref["read"] = False
        if config.read is not None and config.read:
            ref["read"] = True

        self.Resave(litman_db)

    def Note(self, config):
        # Find the requested reference
        litman_db = self.LoadDB(config)
        if config.ref not in litman_db:
            raise ValueError("\n\033[31mRequested reference \033[34m{}\033[31m not in database.\033[0m\n".format(config.ref))
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
            print("\033[5;1m\nNo entries found!\n\033[0m")
            exit()
        if config.all:
            file_list = " ".join([e['file'] for e in entries])
        else:
            file_list = entries[0]['file']
        os.system("open {}".format(file_list))

    def PrintReferences(self, litman_db, entries, config):
        # This flashes because I got carried away
        # with the ANSI formatting
        if len(entries):
            print("\033[1;5m\nMatching entries:\033[0m\n")
        else:
            print("\033[5;1m\nNo entries found!\n\033[0m")

        # Print each selected entry
        for entry in entries:

            # Basic information
            print("{}:{}{}{}{}\n  {}\n    {}"
                  .format('\033[34m{}\033[30m'.format(entry['label']),
                          " \033[7mImportant\033[0m" if entry["important"] else "",
                          " \033[7mPrinted\033[0m" if entry["printed"] else "",
                          " \033[7mTo Read\033[0m" if not entry["read"] else "",
                          " \033[7mNotes\033[0m" if entry["notes"] else "",
                          '\033[4m{}\033[0m'.format(entry['title']),
                          '\033[3m{}\033[0m'.format(', '.join(entry['authors']))))

            # Type specific information
            print("    {} ({})".format(reference_types[entry['type']].FormatSpecificInfo(entry),
                                       entry['year']))

            # Tags, notes and links
            if not config.compact:
                print("  (\033[31m{}\033[30m)".format(' '.join(entry['tags'])))
                for note in entry['notes']:
                    print("\033[2m    - {}\033[0m".format(note))
                if len(entry['citations']) or len(entry['references']):
                    print("  \033[32mCitations:\033[0m")
                    for citation in entry['citations']:
                        cite = litman_db[citation]
                        print("    - {}: {} ({})".format(cite['label'], cite['title'], cite['year']))
                    print("  \033[32mReferences:\033[0m")
                    for reference in entry['references']:
                        ref = litman_db[reference]
                        print("    - {}: {} ({})".format(ref['label'], ref['title'], ref['year']))

            print()

    def Remove(self, config):
        Confirm("Remove reference {}?".format(config.ref))

        # Load the database
        litman_db = self.LoadDB(config)

        # Remove the file
        if config.delete_file:
            os.remove(litman_db[config.ref]['file'])
        else:
            archive_path = '{}/{}'.format(self.LitManFiles, 'archive')
            if not os.path.exists(archive_path):
                os.mkdir(archive_path)
            shutil.move(litman_db[config.ref]['file'],
                        os.path.join(archive_path, os.path.basename(litman_db[config.ref]['file'])))

        # Delete from database
        del litman_db[config.ref]
        self.Resave(litman_db)

    def Resave(self, litman_db):
        if len(litman_db):
            with open(self.LitManDB, 'w') as outfile:
                yaml.dump(litman_db, outfile, default_flow_style=False, allow_unicode=True)
        else:
            os.remove(self.LitManDB)
            with open(self.LitManDB, 'w'):
                os.utime(self.LitManDB, None)            
        self.Cache()
        self.Backup()

    def Summary(self, config):
        # Load the database
        litman_db = self.LoadDB(config)
        categories = []
        tags = []
        for entry in litman_db:
            if litman_db[entry]['category'] not in categories:
                categories.append(litman_db[entry]['category'])
            for tag in litman_db[entry]['tags']:
                if tag not in tags:
                    tags.append(tag)
        categories.sort()
        tags.sort()
        print("\033[1;5m\nSummary:\033[0m\n")
        print("\033[1m{} references\033[0m\n".format(len(litman_db)))
        print("\033[34m{} categories:\t\t\033[31m{} tags:\033[0m"
              .format(len(categories), len(tags)))
        for item in range(max(len(categories), len(tags))):
            if item < len(categories) and item < len(tags):
                print("\033[34m - {:20}\033[31m  - {:20}\033[0m".format(categories[item], tags[item]))
            elif item < len(categories):
                print("\033[34m - {:20}\033[0m".format(categories[item]))
            elif item < len(tags):
                print("\033[31m   {:20}  - {:20}\033[0m".format(' ', tags[item]))
        print()

    def Winnow(self, litman_db, config):
        if litman_db is None:
            return list()
        
        # Return all entries by default
        entries = list(litman_db.values())

        # Reference
        if config.ref is not None:
            entries = []
            for ref in config.ref:
                if ref not in litman_db:
                    raise ValueError("\n\033[31mRequested entry \033[34m{}\033[31m not in database.\033[0m\n".format(ref))
                entries.append(litman_db[ref])

        # Search
        if config.search is not None:
            remove = []
            for i_entry,entry in enumerate(entries):
                for term in config.search:
                    if term.lower() in entry['title'].lower() or \
                       term.lower() in [t.lower() for t in entry['tags']] or \
                       term.lower() in ' '.join([a.lower() for a in entry['authors']]) or \
                       ('journal' in entry and term.lower() in entry['journal'].lower()) or \
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
                if not entry['read']:
                    keep.append(i_entry)
            entries = [e for i,e in enumerate(entries) if i in keep]
        if 'read' in config and config.read:
            keep = []
            for i_entry,entry in enumerate(entries):
                if entry['read']:
                    keep.append(i_entry)
            entries = [e for i,e in enumerate(entries) if i in keep]

        return entries

def Confirm(prompt):
    choice = None
    while choice is None:
        in_choice = input("\n"+prompt+" [y/n] ")
        if in_choice.lower() == 'y' or in_choice.lower() == 'yes':
            choice = 'y'
        if in_choice.lower() == 'n' or in_choice.lower() == 'no':
            choice = 'n'
        print()
        if choice == 'n':
            exit()

def ParseArguments():

    # Set up parser
    parser = argparse.ArgumentParser(prog="litman",
                                     description="Literature Manager: Managing literature for the lit man.")
    parser.add_argument("--no_cache", action='store_true',
                        help="Force load from the YAML file rather than the cache.")
    subparser = parser.add_subparsers(title="litman command", dest="command")
    subparser.required = True

    # Setup
    setup_parser = subparser.add_parser("setup", help="Set up LitMan.")
    setup_parser.add_argument("--litman_dir", required=True,
                              help="Base directory for LitMan to use for its organization.")
    setup_parser.add_argument("--backup_dir", required=True,
                              help="Backup directory for LitMan to store a copy of the database.")

    # Config
    config_parser = subparser.add_parser("config", help="Configuration options.")
    config_parser.add_argument("--litman_dir", help="Base directory for LitMan to use for its organization.")
    config_parser.add_argument("--backup_dir", help="Backup directory for LitMan to store a copy of the database.")

    # Cache
    cache_parser = subparser.add_parser("cache", help="Rebuild the LitMan cache.")

    # Backup
    backup_parser = subparser.add_parser("backup", help="Backup the LitMan database.")

    # Add
    add_parser = subparser.add_parser("add", help="Add reference to LitMan.")
    add_parser.add_argument("--keep_original_file", action='store_true',
                            help="Do not remove the original file after importing to LitMan.")
    add_subparser = add_parser.add_subparsers(title="literature type", dest="type")
    add_subparser.required = True

    ref_parsers = {}
    for ref_type in reference_types:
        ref_parsers[ref_type] = add_subparser.add_parser(ref_type,
                                                         help="Add {}-type reference.".format(ref_type))
        ref_object = reference_types[ref_type]
        for var in sorted(vars(ref_object)):
            if type(vars(ref_object)[var]) == bool:
                ref_parsers[ref_type] .add_argument("--{}".format(var),
                                                    action='store_true')
            else:
                this_type = type(vars(ref_object)[var][0]) if type(vars(ref_object)[var]) == list else type(var)
                this_nargs = '+' if type(vars(ref_object)[var])==list else None
                ref_parsers[ref_type] .add_argument("--{}".format(var),
                                                    required=True,
                                                    type=this_type,
                                                    nargs=this_nargs)

    # Remove
    remove_parser = subparser.add_parser("remove", help="Remove reference.")
    remove_parser.add_argument("--ref", type=str, required=True,
                               help="LitMan reference.")
    remove_parser.add_argument("--delete_file", action='store_true',
                               help="Permanently delete file instead of moving to archive.")

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
    edit_parser.add_argument("--rm_ref", type=int,
                             help="Remove reference (by index, starting from 0) from reference.")
    edit_parser.add_argument("--rm_cite", type=int,
                             help="Remove citation (by index, starting from 0) from reference.")

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

    # Summary
    summary_parser = subparser.add_parser("summary", help="Summarize references in LitMan.")

    # List
    list_parser = subparser.add_parser("list", help="List references in LitMan.")
    list_parser.add_argument("--search", type=str, nargs='+',
                             help="Search terms.")
    list_parser.add_argument("--ref", type=str, nargs='+',
                             help="LitMan reference.")
    list_parser.add_argument("--category", type=str, nargs='+',
                             help="Categories to filter.")
    list_parser.add_argument("--authors", type=str, nargs='+',
                             help="Authors to filter.")
    list_parser.add_argument("--important", action='store_true',
                             help="List only references marked as important.")
    list_parser.add_argument("--to_read", action='store_true',
                             help="List only references marked as to-read.")
    list_parser.add_argument("--read", action='store_true',
                             help="List only references marked as read.")
    list_parser.add_argument("--compact", action='store_true',
                             help="Print items in a compact view.")
    list_parser.add_argument("--clipboard", action='store_true',
                             help="Copy label of top hit to clipboard.")

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
    note_parser.add_argument("--note", type=str, required=True, action='append',
                             help="Add note to reference; multiple entries can be made in bullet-point style.")

    return parser.parse_args()

def SetupLitManEnv(config):

    # Ensure a configuration file
    litman_config_file = "{}/.litman".format(os.path.expanduser("~"))
    if not os.path.exists(litman_config_file):
        print("\nLitMan configuration file not found; making new file {}... ".format(litman_config_file), end='')
        with open(litman_config_file, 'a'):
            os.utime(litman_config_file, None)
        print("\033[32mDone.\033[0m\n")
    else:
        Confirm("Overwrite existing configuration file {}?".format(litman_config_file))

    # Save configuration
    configuration = {'directory':os.path.abspath(config.litman_dir),
                     'backup':os.path.abspath(config.backup_dir)}
    with open(litman_config_file, 'w') as config_file:
        yaml.dump(configuration, config_file)

def main():

    # Parse arguments
    config = ParseArguments()

    # Set up
    if config.command == 'setup':
        SetupLitManEnv(config)
        exit()

    # Check configuration file
    litman_config_file = "{}/.litman".format(os.path.expanduser("~"))
    if not os.path.exists(litman_config_file):
        print("\nLitMan configuration file not found; use \033[1mlitman setup\033[0m to configure LitMan.\n")
        exit()

    # Read litman configuration file
    with open("{}/.litman".format(os.path.expanduser("~")), 'r') as litman_config_file:
        litman_config = yaml.safe_load(litman_config_file)
    if litman_config is None:
        raise RuntimeError("\033[31m\nLitMan configuration file is empty; use \033[1mlitman setup\033[31m to configure.\033[0m\n")

    # Set up program
    litman = LitMan(litman_config)

    # Do stuff
    match config.command:
        case "config":
            print("Config not yet implemented.")
            exit()
        case "cache":
            litman.Cache()
        case "backup":
            litman.Backup()
        case "add":
            litman.Add(config)
        case "edit":
            litman.Edit(config)
        case "remove":
            litman.Remove(config)
        case "mark":
            litman.Mark(config)
        case "link":
            litman.Link(config)
        case "summary":
            litman.Summary(config)
        case "list":
            litman.List(config)
        case "open":
            litman.Open(config)
        case "note":
            litman.Note(config)

if __name__ == "__main__":
    main()
