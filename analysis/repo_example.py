import toml
import os

def get_info():
    """ get all information from github repos """
    datadir = "data/ecosystems"
    dd = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', datadir))
    print (dd)
    orgs = list()
    repos = list()
    for dirpath, dnames, fnames in os.walk(dd):
        for f in fnames:
            with open(dirpath + "/" + f, 'r', encoding='utf-8') as fi:
                content = toml.load(fi)
                orgs.append(content["title"])
                if "repo" in content.keys():
                    repos.extend(content["repo"])
    return [orgs,repos]

[orgs,repos] = get_info()
print ("orgs ", len(orgs))
print ("repos ", len(repos))