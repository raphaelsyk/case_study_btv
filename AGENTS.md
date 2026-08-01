# Repository Rules
- Read 'project_approach.md', to understand project goal and scope and 'docs/reference/Aufgabe_AI_Platform_Engineer.pdf' to get background information
- Read documents in the system_design folder to understand core requirements and already given design decisions

## System Design
- Document every System Design Decision undertaken in 'system_design/02_system_design.md' or 'system_design/02_system_design_data_model.md' if it is with respect to the data model

## Coding rules
- Prefer small classes and methods over collections of free functions. Simple functions are fine when they are the most idiomatic option, but favor object-oriented-programming where it improves structure.
- Keep code typed.
- When adding or editing a public method on a class, add or update a short docstring that states what the method does. Keep it concise and use the Google Docstring format
- Add short comments where the reason for code is not obvious from the code itself, especially for unexpected behavior, external-site quirks, or integration constraints.
- Use `ruff` for both formatting and linting, and `ty` for type checking. Run all three before finishing: `ruff format`, `ruff check`, and `ty check`. When commands, subcommands, options, prompts, or usage examples change, update the README in the same change.
- Do not remove code blocks that allow the user to smoke test/debug the app by entering from a module through `if __name__ == '__main__"` with the debugger. This is for example valid in the earnings_calls/pipeline/orchestrator.py module.

## Smoke tests
- IMPORTANT: If you want to run an end-to-end smoke test or integration test that incorporates calls to an LLM, ask the user for approval before doing so

## Dependency management
- Add Python dependencies with `uv add ...`. Add tooling like `ruff` as dev dependencies with `uv add --dev ...`.
- If a new dependency would simplify the task or materially improve the implementation, make a recommendation and ask for a final decision before adding it.

# Git rules
- Only create commits when the user explicitly asks for one.
- When creating a commit, write a self-contained message that stands on its own without a PR description.
- State the functional changes clearly: what changed, what was added, and what was removed.
- Keep implementation detail high level. Focus on behavior and user-visible impact, not low-level code steps.
- Never use your name as the author and never add it to the commit message
