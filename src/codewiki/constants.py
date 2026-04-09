"""Default constants, paths, and prompt templates for CodeWiki."""

CODEWIKI_DIR = ".codewiki"
WIKI_DIR = "wiki"
CONFIG_FILE = "config.yaml"
INDEX_FILE = "index.md"
LOG_FILE = "log.md"

WIKI_SECTIONS = ["modules", "patterns", "decisions"]

DEFAULT_INCLUDE_GLOBS = [
    "**/*.py", "**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx",
    "**/*.go", "**/*.rs", "**/*.java", "**/*.kt",
    "**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp",
    "**/*.rb", "**/*.php", "**/*.swift", "**/*.scala",
    "**/*.sh", "**/*.bash",
    "**/*.md", "**/*.txt",
    "**/*.yaml", "**/*.yml", "**/*.toml", "**/*.json",
    "**/*.sql",
    "**/Dockerfile", "**/Makefile", "**/Cargo.toml",
    "**/package.json", "**/requirements.txt", "**/go.mod",
]

DEFAULT_EXCLUDE_GLOBS = [
    "**/node_modules/**", "**/__pycache__/**", "**/venv/**", "**/.venv/**",
    "**/dist/**", "**/build/**", "**/target/**", "**/.git/**",
    "**/*.min.js", "**/*.min.css", "**/*.lock", "**/package-lock.json",
    "**/*.egg-info/**", "**/.tox/**", "**/.mypy_cache/**",
    "**/.pytest_cache/**", "**/coverage/**", "**/htmlcov/**",
]

MAX_FILE_SIZE_KB = 500
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.2
DEFAULT_CHUNK_TOKEN_LIMIT = 6000

# Priority filenames — processed first during ingest
PRIORITY_FILENAMES = [
    "README.md", "readme.md", "README.rst", "README",
    "ARCHITECTURE.md", "CONTRIBUTING.md",
    "main.py", "app.py", "index.ts", "index.js", "main.go", "main.rs",
    "lib.rs", "mod.rs", "server.py", "server.ts", "server.js",
    "manage.py", "setup.py", "pyproject.toml", "package.json",
    "Cargo.toml", "go.mod", "Makefile", "Dockerfile",
]

# ──────────────────────────── Prompt Templates ────────────────────────────

PROMPTS = {
    "file_summary": """\
Analyze this source file and produce a structured summary in markdown.

**File:** `{{ file_path }}`
**Language:** {{ language }}

```
{{ content }}
```

Respond with exactly this structure:
- **Purpose**: One-sentence description of what this file does.
- **Key Exports**: Functions, classes, or constants this file exposes.
- **Dependencies**: What this file imports or depends on (internal and external).
- **Patterns**: Notable design patterns, conventions, or techniques used.
- **Complexity**: Low / Medium / High — with a brief justification.\
""",

    "architecture": """\
You are documenting a codebase. Based on the file summaries below, write a \
high-level **Architecture Overview** page in markdown.

{{ file_summaries }}

Structure your response as:
1. **System Overview** — 2-3 sentence description of what this codebase does.
2. **Component Map** — list the major components/modules and their responsibilities.
3. **Data Flow** — describe how data moves through the system.
4. **Key Patterns** — architectural patterns used (MVC, event-driven, microservices, etc.).
5. **Entry Points** — where execution begins, how the system is started.

Use relative markdown links to reference module pages: `[module_name](modules/module_name.md)`.\
""",

    "module_page": """\
Write a wiki page for the **{{ module_name }}** module of this codebase.

**Architecture context:**
{{ architecture_summary }}

**Files in this module:**
{{ file_summaries }}

Structure your response as:
1. **Purpose** — what this module is responsible for.
2. **Key Components** — important classes, functions, or files with brief descriptions.
3. **API Surface** — the public interface other modules use.
4. **Dependencies** — what this module depends on (internal modules and external packages).
5. **Gotchas** — anything surprising, non-obvious, or easy to get wrong.

Use relative links to other wiki pages where relevant.\
""",

    "patterns": """\
Analyze these file summaries from a codebase and identify recurring **design patterns**.

{{ file_summaries }}

For each pattern found, provide:
1. **Pattern Name** — a descriptive name.
2. **Description** — what the pattern is and why it's used here.
3. **Where Used** — which files or modules use this pattern.
4. **Example** — a brief code-level example or reference.

Only include patterns that appear in multiple places. Skip trivial observations.\
""",

    "decisions": """\
Based on these file summaries and any code comments, infer **architectural decisions** \
that were made in this codebase.

{{ file_summaries }}

For each decision, provide:
1. **Decision** — what was decided.
2. **Rationale** — why (inferred from code patterns, comments, or conventions).
3. **Alternatives** — what other approaches could have been taken.
4. **Consequences** — trade-offs of this decision.

Focus on significant structural decisions, not trivial implementation choices.\
""",

    "dependencies": """\
Analyze these file summaries and dependency manifests to create a **Dependency Map**.

{{ file_summaries }}

{% if manifest_content %}
**Dependency manifests:**
```
{{ manifest_content }}
```
{% endif %}

Structure as:
1. **External Dependencies** — third-party libraries/packages with brief purpose.
2. **Internal Dependency Graph** — how modules depend on each other.
3. **Key Integrations** — external services, APIs, or databases the codebase connects to.\
""",

    "onboarding": """\
Based on this architecture overview and module summaries, write an **Onboarding Guide** \
for a new developer joining this project.

**Architecture:**
{{ architecture }}

**Modules:**
{{ module_summaries }}

Structure as:
1. **What This Project Does** — plain-language explanation.
2. **Getting Started** — prerequisites, setup steps (inferred from config files).
3. **Code Tour** — where to look first, key files to understand.
4. **Common Tasks** — how to add a feature, fix a bug, run tests (if inferable).
5. **Concepts to Know** — domain concepts or patterns a newcomer should understand.

Use relative links to other wiki pages.\
""",

    "query_answer": """\
Answer the following question about this codebase using ONLY the wiki pages provided. \
Cite pages using `[Page Title](relative/path.md)` format. If the wiki doesn't contain \
enough information to answer fully, say what's missing.

**Question:** {{ question }}

**Wiki pages:**
{{ pages }}\
""",

    "evolve_update": """\
Update this wiki page to reflect recent code changes. Preserve the existing structure \
and only modify sections affected by the changes. If sections are no longer relevant, \
remove them. If new sections are needed, add them.

**Current wiki page:**
{{ current_page }}

**Changes (git diff):**
```
{{ diff }}
```

**Updated file summaries:**
{{ file_summaries }}

**Recent commit messages:**
{{ commit_messages }}

Return the full updated page content.\
""",
}
