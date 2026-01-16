# Anti-Patterns (Forbidden Behaviors)

These examples show what Claude should **NOT** do.

### ❌ Stopping to Ask for Confirmation
**User**: "Run the feed summarizer."
**Claude (Bad)**: "I found 5 videos. The first one is 'AI News'. It is 45 minutes long. Shall I proceed with downloading and summarizing it?"
**Correction**: Claude should simply verify the duration against the filter (e.g., >30 min) and process it silently if it passes.

### ❌ Stopping for Missing Data
**User**: "Run the feed summarizer."
**Claude (Bad)**: "I cannot find the name of the guest for the second video. What should I put in the guest field?"
**Correction**: Claude should use the default value "Unknown" or "N/A" and continue.

### ❌ Stopping for Output Length
**User**: "Summarize this long podcast."
**Claude (Bad)**: "The summary is very long (over 5000 words). Do you want me to print it all or summarize it further?"
**Correction**: Claude should automatically split the output into `rewritten_part1.md` and `rewritten_part2.md` or output the full text if within limits.

### ❌ Complaining about Missing Tools
**User**: "Run the feed summarizer."
**Claude (Bad)**: "I don't have `xyz-dl` installed."
**Correction**: The skill assumes the environment is set up. If a command fails, log the specific error to a file and move to the next item (Log & Skip).
