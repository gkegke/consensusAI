document.addEventListener("DOMContentLoaded", function() {
    const voteForm = document.getElementById('voteForm');
    const scoreInput = document.getElementById('scoreInput');
    const scoreDisplay = document.getElementById('scoreDisplay');
    const submitBtn = document.getElementById('submitBtn');

    if (!voteForm) return;

    // Force users to explicitly click "Submit My View".
    voteForm.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            return false;
        }
    });

    // 1. Slider Logic
    if (scoreInput) {
        scoreInput.addEventListener('input', function() {
            scoreDisplay.textContent = this.value;
            submitBtn.disabled = false;
        });
        submitBtn.disabled = false;
    }

    // 2. Categorical (Predictive Choice) Logic
    const choiceList = document.getElementById('choice-list');
    const addBtn = document.getElementById('addChoiceBtn');
    const newNameInput = document.getElementById('newChoiceName');
    const otherBalanceDisplay = document.getElementById('otherBalance');
    const allocatedTotalDisplay = document.getElementById('allocatedTotal');
    const choiceError = document.getElementById('choiceError');

    function calculateForecast() {
        if (!choiceList) return;
        
        let userDefinedTotal = 0;
        let hasNonZeroChoice = false;
        const currentNames = [];

        const inputs = choiceList.querySelectorAll('.choice-input');
        inputs.forEach(input => {
            const val = parseFloat(input.value) || 0;
            userDefinedTotal += val;
            if (val > 0) hasNonZeroChoice = true;
            
            // Track names for duplicate checking
            const name = input.closest('.choice-row').querySelector('input[type="hidden"]').value.toLowerCase();
            currentNames.push(name);
        });

        const otherBalance = Math.max(0, 100 - userDefinedTotal);
        
        // Update UI
        if (otherBalanceDisplay) otherBalanceDisplay.textContent = otherBalance.toFixed(1) + "%";
        if (allocatedTotalDisplay) allocatedTotalDisplay.textContent = userDefinedTotal.toFixed(1) + "%";

        // Validation Logic
        const isOverBudget = userDefinedTotal > 100.01;
        const isValid = !isOverBudget && hasNonZeroChoice;

        if (isOverBudget) {
            choiceError.textContent = "Error: Total allocated exceeds 100%.";
            choiceError.style.display = "block";
            allocatedTotalDisplay.style.color = "red";
        } else {
            choiceError.style.display = "none";
            allocatedTotalDisplay.style.color = "inherit";
        }

        submitBtn.disabled = !isValid;
    }

    if (addBtn) {
        addBtn.addEventListener('click', function() {
            const name = newNameInput.value.trim();
            if (!name) return;

            // Duplicate and reserved name checking.
            const normalizedName = name.toLowerCase();
            if (normalizedName === 'other') {
                alert(" 'Other' is automatically calculated. Please enter a specific option.");
                return;
            }

            let exists = false;
            choiceList.querySelectorAll('input[type="hidden"]').forEach(h => {
                if (h.value.toLowerCase() === normalizedName) exists = true;
            });

            if (exists) {
                alert(`Option "${name}" already exists.`);
                return;
            }

            const div = document.createElement('div');
            div.className = "choice-row";
            div.style = "display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding: 10px; background: #e3f2fd; border-radius: 4px; border: 1px solid #90caf9;";
            div.innerHTML = `
                <span style="flex: 1;"><strong>${name}</strong></span>
                <input type="hidden" name="custom_names" value="${name}">
                <div style="display: flex; align-items: center; gap: 5px;">
                    <input type="number" name="custom_values" class="choice-input" value="0" min="0" max="100" step="0.5" style="width: 70px; padding: 5px; text-align: right;">
                    <span>%</span>
                    <button type="button" class="remove-btn" style="background:none; border:none; color:red; cursor:pointer; margin-left:10px;">✕</button>
                </div>
            `;
            choiceList.appendChild(div);
            
            div.querySelector('.choice-input').addEventListener('input', calculateForecast);
            div.querySelector('.remove-btn').addEventListener('click', function() {
                div.remove();
                calculateForecast();
            });

            newNameInput.value = "";
            calculateForecast();
        });

        // Initial binding
        choiceList.querySelectorAll('.choice-input').forEach(i => {
            i.addEventListener('input', calculateForecast);
        });
        
        calculateForecast();
    }
});