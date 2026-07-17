import './style.css';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('webset-form');
  const queryInput = document.getElementById('query-input');
  const countInput = document.getElementById('count-input');
  const entityType = document.getElementById('entity-type');
  const criteriaInput = document.getElementById('criteria-input');
  const codeOutput = document.getElementById('code-output');
  const submitBtn = document.getElementById('submit-btn');
  const apiResponseDiv = document.getElementById('api-response');
  const responseOutput = document.getElementById('response-output');

  // Real-time update code panel
  function updateCodePanel() {
    const query = queryInput.value || "Biggest AI companies by revenue";
    const count = countInput.value || 10;
    const entity = entityType.value;
    const criteria = criteriaInput.value;

    let code = `from search_engine import DeepSearch

ds = DeepSearch()

webset = ds.websets.create(
    search = {
        "query": "${query}",
        "count": ${count}`;

    if (entity) {
      code += `,\n        "entity_type": "${entity}"`;
    }
    if (criteria) {
      code += `,\n        "criteria": "${criteria}"`;
    }

    code += `
    }
)

print(f"Webset created: {webset.id}")`;

    codeOutput.textContent = code;
  }

  // Bind events
  queryInput.addEventListener('input', updateCodePanel);
  countInput.addEventListener('input', updateCodePanel);
  entityType.addEventListener('change', updateCodePanel);
  criteriaInput.addEventListener('input', updateCodePanel);

  // Form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!queryInput.value) return;

    submitBtn.textContent = 'Searching...';
    submitBtn.disabled = true;

    try {
      const response = await fetch('http://localhost:8000/api/websets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: queryInput.value,
          count: parseInt(countInput.value, 10),
          entity_type: entityType.value || null,
          criteria: criteriaInput.value || null
        })
      });

      const data = await response.json();
      
      apiResponseDiv.style.display = 'block';
      responseOutput.textContent = JSON.stringify(data, null, 2);
      
    } catch (err) {
      apiResponseDiv.style.display = 'block';
      responseOutput.textContent = `Error: ${err.message}`;
    } finally {
      submitBtn.textContent = 'Search ↵';
      submitBtn.disabled = false;
    }
  });

  // Initial code update
  updateCodePanel();
});
