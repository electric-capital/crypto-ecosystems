"""
basic example to analyze the repos

more information
github rest api: https://developer.github.com/v3
python wrapper: https://pygithub.readthedocs.io
"""

import toml
import os
import time
from github import Github

g = Github()

def get_info():
    """ get all information from github repos index on disk """
    datadir = "data/ecosystems"
    dd = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', datadir))
    print ("analysing ",dd)
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

def basic_example(repos, name):
    """ simple example which looks for a name in the repo and checks the stars """
    c = 0
    for r in repos[:]:    
        if name in r["url"]:
            repo_name = r["url"].replace("https://github.com/","")
            repo = g.get_repo(repo_name)
            stars = repo.stargazers_count
            if stars > 100:
                print ("repo ", repo_name, " stars", stars)
                #contribs = repo.get_contributors()
                #print (contribs)
                c+=1
            time.sleep(0.1)

    print ("repos with %s in its name %i and more than %i stars"%(name,c,100))


if __name__ == '__main__':
    [orgs,repos] = get_info()
    print ("orgs ", len(orgs))
    print ("repos ", len(repos))
    basic_example(repos, "bitcoin")
    #basic_example(repos, "trading")

