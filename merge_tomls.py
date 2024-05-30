from tomlkit import parse, dumps

near_toml = '/Users/spark_near/Documents/GitHub/s-n-park/crypto-ecosystems/data/ecosystems/n/near.toml'

# Load the main TOML file
with open(near_toml, 'r') as file:
    main_data = parse(file.read())

# Load the extra TOML file
with open('extra.toml', 'r') as file:
    extra_data = parse(file.read())

# Extract the repo lists
main_repos = main_data.get('repo', [])
extra_repos = extra_data.get('repo', [])

# Merge the repo lists and remove duplicates
merged_repos = {repo['url']: repo for repo in main_repos + extra_repos}.values()

# Sort the repos by URL in a case-insensitive manner
merged_repos = sorted(merged_repos, key=lambda repo: repo['url'].lower())

# Add the merged repos back to the main data
main_data['repo'] = list(merged_repos)

# Write the merged data back to the main TOML file
with open(near_toml, 'w') as file:
    file.write(dumps(main_data))