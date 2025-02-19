# Contributing

This project welcomes contributions and suggestions. Most contributions require you to
agree to a Contributor License Agreement (CLA) declaring that you have the right to,
and actually do, grant us the rights to use your contribution. For details, visit
https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

---

## 🚀 Suggested Workflow for an Effective Development Process

This workflow enables the team to collaboratively build a robust, user-centered software product while upholding high technical and product standards.

### 1. Start with a New Issue
Kick off your contribution by creating a new issue in the repository's issue tracker. Use GitHub Issues for tracking bugs and requesting features.

🔗 **[GitHub Issues Quickstart Guide](https://docs.github.com/en/issues/tracking-your-work-with-issues/quickstart#:~:text=Opening%20a%20blank%20issue%201%20On%20GitHub.com%2C%20navigate,uses%20issue%20templates%2C%20click%20Open%20a%20blank%20issue).**

---

### 2. Clone the Repository
```bash
git clone https://github.example.com/{your_project}.git
```

---

### 3. Set Up Your Development Environment
#### Modify `environment.yaml`
```yaml
name: my-template-environment
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.10
  - pip
  - pip:
      - -r requirements.txt
      - -r requirements-codequality.txt
```

#### Creating and Activating the Conda Environment
For Windows:
```bash
conda env create -f environment.yaml
conda activate pa-ai-env
```
For Linux (or WSL):
```bash
make create_conda_env
conda activate pa-ai-env
```

---

### 4. Create a New Branch for Features or Bug Fixes
```bash
git checkout -b feature/YourFeatureName_or_bugfix/YourBugFixName
```
📌 **Branching Strategy**
- `feature/new_feature` → Development
- `staging` → Testing & validation
- `main` → Production

![Branching Strategy Diagram](utils/images/flow.png)

---

### 5. Incorporate Tests and Update Documentation
- **Unit Tests** → `tests/test_my_module.py`
- **Integration Tests** → `tests/integration/`
- **Documentation** → Update docstrings & README

---

### 6. Run Tests & Style Checks
```bash
make run_code_quality_checks
make run_tests
```

---

### 7. Update Requirements & Document Changes
**Versioning:**
- **Major (5.0.0)** → Breaking changes
- **Minor (5.1.0)** → New features
- **Patch (5.1.4)** → Fixes

---

### 8. Commit & Push Your Changes
```bash
git commit -m 'TypeOfChange: Brief description of the change'
git push origin YourBranchName
```

---

### 9. Create a Well-Documented Pull Request
- Open a pull request (PR) targeting either the `staging` or `main` branch.
- Link to an issue: `Closes #XXX`
- Follow PR template
- Await **WG review** & GitHub CI checks

🔗 **[GitHub PR Guide](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests).**

---

## 📦 Additional Setup Steps
### 🔧 Setting Up VSCode for Jupyter Notebooks
- Install `Python` & `Jupyter` extensions
- Attach Conda kernel: `pa-ai-env`
- Run `01-indexing-content.ipynb`

### 🔍 Configuring Pre-commit Hooks
```bash
make set_up_precommit_and_prepush
```

---

## 💡 Development Tips
### 🧪 Commit to Testing Early
- Quick identification of bugs
- Improves maintainability
- Understands performance

### 📓 Using `%%ipytest` for Interactive Testing
```python
%%ipytest
def test_add_numbers():
    assert add_numbers(1, 2) == 3
    assert add_numbers(-1, 1) == 0
```

---

## 🛠 Working Groups
Each Working Group (WG) oversees a key area of the project.

| Working Group | Scope |
|--------------|----------------------------------------------|
| **Application Deployment WG** | CI/CD, containerization, branching strategy, Cloud provisioning, security, automation |
| **App Development WG** | Frontend, backend, features, APIs |
| **AIOps WG** | Prompt engineering, model evaluation, monitoring, extraction |

📌 **WG leads track tasks in GitHub Projects and coordinate with the Steering Committee for releases.**

---

## 🚀 Release Strategy
### 📋 Release Planning
- The **Steering Committee** defines release scope
- **WG leads commit features & fixes**
- Progress tracked in **GitHub Projects**

### 🔀 Branching Strategy
- `main` → Stable
- `release/x.y` → In-progress releases
- `hotfix/x.y.z` → Critical patches

### 📊 Managing Releases in GitHub Projects
1. Create **Release Project**
2. Add issues & PRs
3. Track progress (`To Do` → `In Progress` → `Done`)
4. Final validation
5. **Cut release branch & publish notes**

---

## 🔧 Steering Committee
A **three-person Steering Committee** oversees governance, release planning, and issue resolution.

**Responsibilities:**
- Approving new Working Groups
- Resolving PR disputes
- Roadmap alignment
- Managing cloud resources

📌 **Steering Committee Members:**
| Member | Working Group |
|--------|--------------|
| **[Pablo Salvador Lopez](https://github.com/pablosalvador10)** | App Development |
| **[Marcin Jimenez](https://github.com/marcjimz)** | AIOps |
| **[Jin Lee](https://github.com/marcjimz)** | App Deployment |

---

## 💬 Communication Channels
| Platform | Purpose |
|----------|---------|
| **Microsoft Teams** | Discussions & announcements |
| **GitHub Issues** | Bugs, features, proposals |
| **GitHub PRs** | Code reviews & merges |
| **GitHub Projects** | Task & release tracking |

📌 **Pending: We hold bi-weekly/monthly syncs for updates, demos, and proposals.**

---

### 🌟 Summary
✅ **Follow the structured workflow**
✅ **Test early & update documentation**
✅ **Engage in PR reviews & WG discussions**
✅ **Stay connected via Teams & GitHub**

💙 *We appreciate all contributions! Your efforts make this project stronger!* 🚀
