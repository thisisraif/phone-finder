// DOM Elements
const list = document.getElementById('priority-list');
const submitBtn = document.getElementById('submit-btn');
const result = document.getElementById('result');
const budgetSelect = document.getElementById('budget');

// Make list items draggable
function setupDragAndDrop() {
  let draggedItem = null;

  list.querySelectorAll('.priority-item').forEach(item => {
    item.addEventListener('dragstart', (e) => {
      draggedItem = item;
      e.dataTransfer.setData('text/plain', item.dataset.id);
      item.classList.add('opacity-50');
    });

    item.addEventListener('dragend', () => {
      draggedItem.classList.remove('opacity-50');
      updateRanks();
    });

    item.addEventListener('dragover', (e) => {
      e.preventDefault();
    });

    item.addEventListener('drop', (e) => {
      e.preventDefault();
      const dropTarget = e.target.closest('.priority-item');
      
      if (draggedItem && dropTarget && draggedItem !== dropTarget) {
        const allItems = Array.from(list.children);
        const draggedIndex = allItems.indexOf(draggedItem);
        const dropIndex = allItems.indexOf(dropTarget);
        
        if (draggedIndex < dropIndex) {
          dropTarget.after(draggedItem);
        } else {
          dropTarget.before(draggedItem);
        }
        updateRanks();
      }
    });
  });
}

// Update rank numbers
function updateRanks() {
  list.querySelectorAll('.priority-item').forEach((item, index) => {
    item.querySelector('.rank').textContent = index + 1;
  });
}

// Handle form submission
async function handleSubmit() {
  const budget = budgetSelect.value;
  const priorities = Array.from(list.children).map((item, index) => ({
    // Convert data-id to lowercase for consistency with backend
    feature: item.dataset.id.toLowerCase(),
    rank: index + 1
  }));

  // Show loading state
  submitBtn.disabled = true;
  submitBtn.textContent = 'Finding Recommendations...';
  result.classList.add('hidden');

  try {
    const response = await fetch('http://localhost:8000/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budget, priorities })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to get recommendations');
    }

    const data = await response.json();
    displayResults(data);
  } catch (error) {
    showError(error.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Priorities';
  }
}

// Display results
function displayResults(data) {
  result.innerHTML = '';
  result.classList.remove('hidden', 'error-message');

  if (!data.results || data.results.length === 0) {
    result.textContent = 'No phones found matching your criteria. Try adjusting your preferences.';
    return;
  }

  const container = document.createElement('div');
  container.className = 'space-y-4';

  // Add header
  const header = document.createElement('h3');
  header.className = 'text-xl font-bold text-center mb-4';
  header.textContent = `Top ${data.count} Recommendations`;
  container.appendChild(header);

  // Add each phone result
  data.results.forEach(phone => {
    const card = document.createElement('div');
    card.className = 'phone-card';
    card.innerHTML = `
      <div class="phone-title">
        <span>${phone.Brand} ${phone.Model}</span>
        <span class="phone-score">Score: ${phone.Total_Score.toFixed(2)}</span>
      </div>
      <div class="phone-ratings">
        <div>Brand: <span class="font-medium">${phone.Brand_Rating}</span></div>
        <div>Processor: <span class="font-medium">${phone.Processor_Rating}</span></div>
        <div>Battery: <span class="font-medium">${phone.Battery_Rating}</span></div>
        <div>Camera: <span class="font-medium">${phone.Camera_Rating}</span></div>
      </div>
    `;
    container.appendChild(card);
  });

  result.appendChild(container);
}

// Show error message
function showError(message) {
  result.textContent = `Error: ${message}`;
  result.classList.remove('hidden');
  result.classList.add('error-message');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupDragAndDrop();
  submitBtn.addEventListener('click', handleSubmit);
});