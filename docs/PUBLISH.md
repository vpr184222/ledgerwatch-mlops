# Publish this repository

Create an empty GitHub repository with the same name as this project. Do not select
GitHub's automatic README or license; both are already included here.

From this project's root folder (not its parent):

```sh
git init -b main
git add .
git status
git commit -m "Build end-to-end portfolio project"
git remote add origin https://github.com/YOUR_USERNAME/REPOSITORY_NAME.git
git push -u origin main
```

Replace the username and repository name with your own. Review `git status` before
committing. `.gitignore` excludes runtime files, secrets, and installed dependencies.
If Git asks for author identity, set your name and a GitHub verified email for this repo.
Authenticate through GitHub's browser flow, SSH, or Git Credential Manager. Never paste
a password or access token into a chat or commit one into the repository.

In GitHub's About section add the description and topics suggested in the README.
After publishing, check the Actions tab. CI runs Python tests, the TypeScript production
build, and Docker builds. A configured workflow is not evidence that a remote run passed.

Add a short demo video after running the walkthrough. Both repositories are independent;
publish each in its own GitHub repository.
