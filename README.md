Continuous Integration tooling to integrate with Flagsmith.

## Code References

Keep track of feature flags used throughout the codebase. Needs an [Organisation Admin API Key](https://docs.flagsmith.com/integrating-with-flagsmith/flagsmith-api-overview/admin-api/authentication). See related [documentation](https://docs.flagsmith.com/managing-flags/code-references).

<details>
<summary>
<h3>Setting up with GitHub (Simple)</h3>
<br>Add a new GHA workflow that points to the reusable workflow.
</summary>

```yaml
# .github/workflows/flagsmith-code-references.yml
name: Flagsmith Code References

on:
  push:
    branches:
      - main

jobs:
  collect-code-references:
    name: Collect
    uses: Flagsmith/ci/.github/workflows/collect-code-references.yml@v1.0.0
    with:
      flagsmith_project_id: ${{ fromJSON(vars.FLAGSMITH_PROJECT_ID) }}  # Obtain from your Flagsmith dashboard URL
      flagsmith_admin_api_url: https://api.flagsmith.com  # Or your custom Flagsmith API URL
    secrets:
      flagsmith_admin_api_key: ${{ secrets.FLAGSMITH_CODE_REFERENCES_API_KEY }}
```

</details>

<details>
<summary>
<h3>Setting up with GitHub (Advanced)</h3>
<br>Individual actions are available for customising the integration workflow.
</summary>

```yaml
# .github/workflows/flagsmith-code-references.yml
name: Flagsmith Code References

on:
  push:
    branches:
      - main

jobs:
  collect-code-references:
    name: Collect code references
    runs-on: ubuntu-latest
    permissions:
      contents: read
    env:
      FLAGSMITH_API_URL: https://api.flagsmith.com  # Or your custom Flagsmith API URL
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Fetch feature names
        id: fetch-feature-names
        uses: Flagsmith/ci/.github/actions/fetch-feature-names@v1.0.0
        with:
          flagsmith_project_id: ${{ vars.FLAGSMITH_PROJECT_ID }}
          flagsmith_admin_api_url: ${{ env.FLAGSMITH_API_URL }}
          flagsmith_admin_api_key: ${{ secrets.FLAGSMITH_CODE_REFERENCES_API_KEY }}

      - name: Scan code references
        id: scan-code-references
        uses: Flagsmith/ci/.github/actions/scan-code-references@v1.0.0
        with:
          feature_names: ${{ steps.fetch-feature-names.outputs.feature_names }}

      - name: Upload code references
        uses: Flagsmith/ci/.github/actions/upload-code-references@v1.0.0
        with:
          code_references: ${{ steps.scan-code-references.outputs.code_references }}
          flagsmith_project_id: ${{ vars.FLAGSMITH_PROJECT_ID }}
          flagsmith_admin_api_url: ${{ env.FLAGSMITH_API_URL }}
          flagsmith_admin_api_key: ${{ secrets.FLAGSMITH_CODE_REFERENCES_API_KEY }}
          repository_url: ${{ github.server_url }}/${{ github.repository }}
          revision: ${{ github.sha }}
```

</details>

---

Support to other vendors is planned.
