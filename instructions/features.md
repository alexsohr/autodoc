<!-----



Conversion time: 0.924 seconds.


Using this Markdown file:

1. Paste this output into your source file.
2. See the notes and action items below regarding this conversion run.
3. Check the rendered output (headings, lists, code blocks, tables) for proper
   formatting and use a linkchecker before you publish this page.

Conversion notes:

* Docs to Markdown version 1.0β44
* Wed Jun 11 2025 17:57:14 GMT-0700 (PDT)
* Source doc: I need the output in markdown language
----->



### AutoDoc: Feature Implementation Plan

Here is a proposed plan for developing the new features for your AutoDoc project. We can tackle these one by one.


### Feature 1: .autodoc Folder & Repository-Specific Configuration

**Goal:** Scan the target repository for an .autodoc directory and use the files within to guide the documentation process.

**Educational Context:** This feature follows a powerful software design principle called "convention over configuration." Instead of requiring users to navigate complex settings pages, we rely on a conventional folder name (.autodoc) placed at the project's root. This pattern is common in the developer ecosystem (e.g., .github for GitHub Actions, .vscode for editor settings) because it co-locates configuration with the code it affects. It empowers repository owners to customize AutoDoc's behavior for their specific project by simply adding files.

The config.yml file uses YAML, a popular data format chosen for its human-readability—it's cleaner than JSON and supports comments, which is great for explaining settings. Meanwhile, autodoc-instruction.md lets users give direct, natural language instructions to the LLM, essentially providing it with a "style guide" to follow for that specific repository.

**Implementation Plan:**



1. **Modify Data Pipeline (Backend - **api/data_pipeline.py**):**
    * After cloning a repository, add a step to check for the existence of an .autodoc directory at the root.
    * If it exists, parse the files within. The resulting configuration object should be stored in memory or alongside the cached repo data, creating a specific profile for that repository's generation task.
2. **Process **autodoc-instruction.md** (Backend - **api/rag.py**):**
    * If autodoc-instruction.md is found, read its entire contents into a string.
    * This content should be treated as a high-priority system prompt. In the logic that constructs the final prompt for the LLM, prepend this user-defined instruction. For example: final_prompt = user_instruction_text + original_system_prompt. This ensures the LLM receives the custom guidance first, allowing it to tailor the tone, style, focus, and even the format of the generated documentation.
3. **Process **config.yml** (Backend):**
    * Use a robust Python library like PyYAML (pip install pyyaml) to safely parse the config.yml file using yaml.safe_load().
    * **File Filtering:**
        * Implement logic to handle include and exclude lists. Python's glob and fnmatch libraries will be perfect for supporting familiar wildcard patterns (*, **/*, *.py).
        * The filtering should follow a clear order of operations: start with the global rules from repo.json, then apply the repository-specific include/exclude rules from config.yml. This allows for fine-grained control.
    * **Merge Back Configuration:**
        * Read keys like enable_merge_back: true, target_folder, and target_file_name.
        * Store these values in the repository's session configuration, making them readily available for the automated merge back feature (Feature 3).


### Feature 2: Automated Trigger via Bitbucket Webhook

**Goal:** Provide a secure endpoint to receive Bitbucket webhooks, enabling external events to trigger the documentation generation process automatically.

**Educational Context:** A webhook is a mechanism for one application (Bitbucket) to send real-time information to another (AutoDoc) when a specific event occurs, like a push to a repository. Think of it as an automated notification system that says, "Hey, something just happened that you might care about!" Securing this is vital. We use a "shared secret" key to generate an HMAC signature, which acts like a tamper-proof seal, proving the request is authentic and came from Bitbucket, not an attacker. The immediate 202 Accepted response tells Bitbucket "I've received your request and will work on it," allowing for longer-running tasks without making the sender wait.

**Implementation Plan:**



1. **Webhook Endpoint Creation (Backend - **api/api.py**):**
    * Define a new FastAPI endpoint: POST /webhook/bitbucket. This endpoint will be the entry point for all Bitbucket events.
    * It should be designed to handle asynchronous tasks. Upon receiving a valid request, it should immediately return a 202 Accepted response and start the generation process in the background using FastAPI's BackgroundTasks.
2. **Security & Validation:**
    * **Secret Key Validation:** The endpoint MUST be secured. Add a new environment variable, BITBUCKET_WEBHOOK_SECRET. Users will configure this same secret in their Bitbucket webhook settings.
    * On every incoming request, calculate the HMAC-SHA256 signature of the raw request body using the secret key. Compare your calculated signature to the one provided in the X-Hub-Signature request header to authenticate the request. Reject any requests that do not match to prevent unauthorized use.
3. **Event Handling & Parsing:**
    * The primary event to handle is repo:push on the repository's main branch. This is generally more reliable than pullrequest:fulfilled as it captures all merges and direct pushes to the main line of development.
    * Parse the JSON webhook payload to extract critical information: Repository Name and URL (repository.links.html.href) and the branch that was pushed to (push.changes[0].new.name).
4. **Triggering the Generation Workflow:**
    * Once the request is validated and parsed, confirm that the push event occurred on the repository's main/default branch.
    * If it meets the criteria, add the documentation generation task to the background queue, passing the repository URL as a parameter. This will invoke the same core logic used by the manual "Generate Wiki" button, ensuring consistent behavior.


### Feature 3: Automated Merge Back to Bitbucket

**Goal:** After a successful documentation generation, automatically commit the new llms.txt and updated documentation files to a new feature branch in the target Bitbucket repository and create a pull request.

**Educational Context:** This feature evolves AutoDoc from a read-only tool to a true "robot developer" that actively contributes back to a project. It treats the user's Git repository like a database that our application can programmatically write to. Instead of pushing changes directly to the main branch (which is risky and bad practice), we use a "feature branch." This best practice isolates our documentation updates, allowing them to be reviewed through a "pull request" (PR)—a formal request to merge our changes. This entire process is automated using a Bitbucket "App Password," a secure, revocable credential with limited permissions (e.g., only repository write access), making it safer than using a personal password for automation.

**Implementation Plan:**



1. **Configuration & Authentication:**
    * This feature should be opt-in, controlled by a setting in .autodoc/config.yml (e.g., enable_merge_back: true).
    * **Authentication:** The system requires write access. Define new environment variables for a Bitbucket App Password: BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD. These credentials will be used for all Git and API operations.
2. **Git Operations Module (Backend - New Module e.g., **api/git_operations.py**):**
    * Use a robust Python Git library like GitPython (pip install gitpython) to handle all Git commands programmatically.
    * After the documentation generation is complete, this module will be invoked with the generated file contents.
    * **Process:**
        1. Clone the target repository using the configured username and app password.
        2. Create a new, uniquely named feature branch (e.g., autodoc/docs-update-YYYY-MM-DD-HHMMSS).
        3. Clear existing documentation in the target_folder if it exists, to handle file deletions or renames gracefully.
        4. Write the newly generated documentation files to the target_folder specified in .autodoc/config.yml.
        5. Write the generated llms.txt file (from Feature 6) to the repository root.
        6. Stage all changes using git add ..
        7. Commit the changes with a standardized, descriptive message following conventional commit standards, e.g., docs(autodoc): Update project documentation and llms.txt.
        8. Push the new branch to the remote Bitbucket repository.
3. **Pull Request Creation Module (Backend - New Module e.g., **api/bitbucket_client.py**):**
    * This module will handle interactions with the Bitbucket Cloud REST API using a library like requests.
    * **Process:**
        9. After the Git push is successful, make an authenticated POST request to the Bitbucket API endpoint: https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests.
        10. The request body will be a JSON object containing a clear title ("AutoDoc Documentation Update"), a detailed description (e.g., "Automated documentation generated based on recent changes."), the source branch, the destination branch, and a flag to close the source branch on merge.


### Feature 4: Native MCP Server with FastMCP

**Goal:** Expose AutoDoc's wiki data and "Ask" feature through a runnable, local MCP server script built with the fastmcp library.

**Educational Context:** MCP acts like a "USB-C port for AI," standardizing how AI agents use tools. We will use the fastmcp Python library to build a native server, making AutoDoc a first-class citizen in the MCP ecosystem. This server will be a **self-contained Python script** that an MCP client (like an IDE or another AI agent) can run locally. This approach is powerful because it allows the server to securely access local data (like AutoDoc's cache) while exposing its capabilities through the standard MCP protocol. This enables "tool-using agents" to call our specific functions to get information and complete a task.

**Implementation Plan:**

1. **Integrate FastMCP Library:**
    * Add fastmcp to requirements.txt file. This keeps the MCP server's dependencies separate from the main API.
2. **Create Server Script in api folder:**
    * Inside this folder, create a runnable Python script: mcp-server.py.
    * This script will define the server and its tools using fastmcp components. It should not be mounted on the main FastAPI app.
3. **Define Server-Side Parameter (in **mcp-server.py**):**
    * Inside the server script, define repo_url as a required parameter using ServerSideParameter from the fastmcp library.
    * This ensures that any client attempting to run this server *must* provide a target repository URL upon connection, making the server's context explicit.
4. **Implement MCP Tools (in **mcp-server.py**):**
    * Use the @tool decorator to define the async functions that will be exposed as tools.
    * **Crucially, these tools will not import from the **api** module directly.** They will communicate with the main AutoDoc API (nextjs) over HTTP to fetch data . This decouples the two components.
    * read_wiki_structure()**:** This tool will access the repo_url provided at startup and make a GET request to a new endpoint on the main API (e.g., http://localhost:3000/api/wiki-structure?repo_url=...) to get the list of topics.
    * read_wiki_contents(topic: str)**:** This tool will make a GET request to a new endpoint (e.g., http://localhost:3000/api/wiki-content?repo_url=...&topic=...) to get the content.
    * ask_question(question: str)**:** This tool will make a POST request to the existing "Ask" feature's API (eg., http://localhost:3000/api/chat/completions?...) endpoint, passing the repo_url and question.
5. **Autodoc server url:**
    * Read the autodoc server url from environment variable AUTODOC_SERVER_URL


### Feature 5: MCP Configuration UI for Local Server

**Goal:** Provide users with a simple, command-based JSON configuration to easily run the local AutoDoc MCP server.

**Educational Context:** This feature focuses on user experience and ease of integration. Since our MCP server is a local script located in its own directory, the client needs to know exactly how to run it. The JSON configuration block is a standard way to tell an MCP client *which local command to execute* and *what arguments to pass* to start the server for a specific repository. By generating this command automatically, we eliminate manual setup and potential errors for the end-user.

**Implementation Plan:**



1. **Add UI Element (Frontend - **src/components/**):**
    * Create a new React component. After a repository's wiki has been generated, display a prominent button or link like "Get MCP Config".
    * Clicking this button will open a modal window displaying the configuration.
2. **Generate and Display JSON for Command-Based Server:**
    * The component will display a formatted JSON block. The path in the args array now points to the new, self-contained module. The &lt;TARGET_REPOSITORY_URL> will be the repo being viewed.
    
    ```json
    {
        "mcpServers": {
            "autodoc-repo-name": {
            "command": "python",
            "args": [
                "-m",
                "mcp.server",
                "--param",
                "repo_url=&lt;TARGET_REPOSITORY_URL>"
            ]
            }
        }
    }
    ```
3. 
4. **Add "Copy to Clipboard" Button:**
    * Include a button that allows the user to easily copy the entire JSON configuration block to their clipboard, providing immediate utility and a smooth user journey.


### Feature 6: llms.txt Generation

**Goal:** Generate a structured llms.txt file based on the generated wiki and repository analysis.

**Educational Context:** The llms.txt file is an emerging standard designed to solve a key problem: LLMs have a limited "context window," which is like a person's short-term memory. They can't read an entire complex website or codebase at once. The llms.txt file acts as a curated "table of contents" or a high-level summary. It points the LLM directly to the most important, AI-friendly information (like plain Markdown files), saving processing time and improving the accuracy of its understanding. By creating this file, we make our documented repository a better "citizen" of the AI ecosystem, enabling more efficient and accurate interactions with any LLM that follows the standard.

**Implementation Plan:**



1. **Dynamic **llms.txt** Generation (Backend - New Module/Function):**
    * Create a new function that runs after the main documentation/wiki is generated. This function will assemble the content for the llms.txt file in Markdown format.
    * **H1 Title:** Use the repository name as the main title (e.g., # AutoDoc).
    * **Blockquote Summary:** Make a dedicated LLM call with a specific prompt (e.g., "Summarize this project in a single, concise paragraph for a technical audience.") to generate the summary. Use the already generated high-level documentation as context for this call to ensure consistency.
    * **H2 Sections & Links:**
        * Dynamically create sections like ## Docs and ## Key Modules based on the structure of the generated wiki.
        * For each major topic or page in the wiki, create a list item with a link. The link must be a relative path that will be valid once committed to the repository (e.g., [Quick Start](docs/quickstart.md)). This requires coordination with the target_folder from the .autodoc/config.yml.
    * Save the generated Markdown content into a file named llms.txt.
2. **Integrate with Merge Back Workflow:**
    * The llms.txt file should be treated as a core artifact of the generation process, just like the other wiki files.
    * The "Merge Back" logic in **Feature 3** must be aware of this file and ensure it is committed to the root of the new feature branch alongside the other documentation files.
    * 