# Repository Rules

## Coding rules
- Prefer small classes and methods over collections of free functions. Simple functions are fine when they are the most idiomatic option, but favor object-oriented-programming where it improves structure.
- Keep code typed.
- When adding or editing a public method on a class, add or update a short docstring that states what the method does. Keep it concise and use the Google Docstring format
- Add short comments where the reason for code is not obvious from the code itself, especially for unexpected behavior, external-site quirks, or integration constraints.
- Use `ruff` for both formatting and linting, and `ty` for type checking. Run all three before finishing: `ruff format`, `ruff check`, and `ty check`. When commands, subcommands, options, prompts, or usage examples change, update the README in the same change.


## Dependency management
- Add Python dependencies with `uv add ...`. Add tooling like `ruff` as dev dependencies with `uv add --dev ...`.
- If a new dependency would simplify the task or materially improve the implementation, make a recommendation and ask for a final decision before adding it.

# Git rules
- Only create commits when the user explicitly asks for one.
- When creating a commit, write a self-contained message that stands on its own without a PR description.
- State the functional changes clearly: what changed, what was added, and what was removed.
- Keep implementation detail high level. Focus on behavior and user-visible impact, not low-level code steps.
- Never use your name as the author and never add it to the commit message
