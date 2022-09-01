#!/usr/bin/env bash
set -eux

# Build the docs.
pdoc --html src/pyfreedb

# Figure out which commit this release is on.
head=$(git rev-parse HEAD)

# Note that the gh-pages branch is already cloned in the previous workflow step.
# Move the docs to the latest docs folder.
rm -rf gh-pages/latest
mkdir -p gh-pages/latest
cp -R html/pyfreedb/* gh-pages/latest

# Copy the docs folder into the correct release version.
mkdir -p gh-pages/${RELEASE_VERSION}
cp -R gh-pages/latest/* gh-pages/${RELEASE_VERSION}

# Remove the original HTML folder.
rm -rf html

# Handle the file changes in gh-pages branch.
cd gh-pages
git add .

if git diff --staged --quiet; then
    echo "$0: No changes to commit."
    exit 0
fi

# Note that there is no separate token that we need to create here.
# This will work just fine without any personal access token.
if ! git config user.name; then
    git config user.name 'GitHub Pages Bot'
    git config user.email 'github-pages-bot@users.noreply.github.com'
fi

git commit -m "CI: Update docs for release ${RELEASE_VERSION} ($head)"
git push origin gh-pages
