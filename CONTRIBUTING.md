# Contributing

Clone the repository. Move into the directory on your terminal.

Install dependencies for development.

```sh
uv sync --all-extras
```

Install pre-commit to run a battery of automatic quick fixes against your work.

```sh
uv run pre-commit install
```

Run tests.

```sh
uv run pytest
```

Before you release your package, be sure to customize the `setup.py` file to fit your project.

## Releasing

# Releasing

Our release process is automated as a [continuous deployment](https://en.wikipedia.org/wiki/Continuous_deployment) via the [GitHub Actions](https://github.com/features/actions) framework. The logic that governs the process is stored in the `workflows` directory.

That means that everything necessary to make a release can be done with a few clicks on the GitHub website. All you need to do is make a [tagged release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), then wait for the computers to handle the job.

Before you can begin, you have to do the following one-time configuration:

* Visit PyPI and [create an API key](https://pypi.org/help/#apitoken) with permission to release a package
* Save the key as a secret called `PYPI_API_TOKEN` [in your repository settings](https://docs.github.com/en/codespaces/managing-codespaces-for-your-organization/managing-encrypted-secrets-for-your-repository-and-organization-for-github-codespaces)

Once that is done, you can automatically release new versions. Here’s how to do it, step by step. The screenshots are from a different repository, but the process is the same.

## 1. Go to the releases page

The first step is to visit your repository's homepage and click on the "releases" headline in the right rail.

![Release button](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-releases-button.png)

## 2. Click 'Draft a new release'

Note the number of the latest release. Click the "Draft a new release" button in the upper-right corner. If you don't see this button, you do not have permission to make a release. Only the maintainers of the repository are able to release new code.

![Draft button](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-draft-button.png)

## 3. Create a new tag

Think about how big your changes are and decide if you're a major, minor or patch release.

All version numbers should feature three numbers separated by the periods, like `1.0.1`. If you're making a major release that isn't backwards compatible, the latest release’s first number should go up by one. If you're making a minor release by adding a feature or major a large change, the second number should go up. If you're only fixing bugs or making small changes, the third number should go up.

If you're unsure, review the standards defined at [semver.org](https://semver.org) to help make a decision. In the end don't worry about it too much. Our version numbers don't need to be perfect. They just need to be three numbers separated by periods.

Once you've settled on the number for your new release, click on the "Choose a tag" pull down.

![Tag button](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-tag-button.png)

Enter your version number into the box. Then click the "Create new tag" option that appears.

![Tag dropdown](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-name-tag.png)

## 4. Name the release

Enter the same number into the "Release title" box.

![Name box](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-name-release.png)

## 5. Auto-generate release notes

Click the "Auto-generate release notes" button in the upper right corner of the large description box.

![Auto-generate release notes button](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-changelog-button.png)

That should fill in the box below. What appears will depend on how many pull requests you've merged since the last release.

![Auto-generate release notes results](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-changelog-entered.png)

## 6. Publish the release

Click the green button that says "Publish release" at the bottom of the page.

![Publish button](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-publish-button.png)

## 7. Wait for the Action to finish

GitHub will take you to a page dedicated to your new release and start an automated process that release our new version to the world. Follow its progress by clicking on the Actions tab near the top of the page.

![Release page](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-release-published.png)

That will take you to the Actions monitoring page. The task charged with publishing your release should be at the top.

![Actions page](https://raw.githubusercontent.com/palewire/python-open-source-template/main/.github/images/releasing-actions-start.png)

After a few minutes, the process there should finish and show a green check mark. When it does, visit your package’s page on [PyPI](https://pypi.org/), where you should see the latest version displayed at the top of the page.

If the action fails, something has gone wrong with the deployment process. You can click into its debugging panel to search for the cause or ask the project maintainers for help.
