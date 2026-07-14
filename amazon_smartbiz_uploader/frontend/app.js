document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('product-rows-container');
    const template = document.getElementById('product-row-template');
    const addRowBtn = document.getElementById('add-row-btn');
    const generateBtn = document.getElementById('generate-btn');
    const resultsSection = document.getElementById('results-section');
    const downloadLink = document.getElementById('download-link');
    const btnText = generateBtn.querySelector('.btn-text');
    const spinner = generateBtn.querySelector('.spinner');

    let rowCount = 0;

    // Initialize with one row
    addRow();

    // Event Listeners
    addRowBtn.addEventListener('click', addRow);
    generateBtn.addEventListener('click', handleGenerate);

    function addRow(initialValues = null) {
        rowCount++;
        const clone = template.content.cloneNode(true);
        const rowElement = clone.querySelector('.product-row');
        
        if (initialValues) {
            rowElement.querySelector('.input-sku').value = initialValues.sku || '';
            rowElement.querySelector('.input-business-cat').value = initialValues.businessCat || '';
            rowElement.querySelector('.input-product-cat').value = initialValues.productCat || '';
            rowElement.querySelector('.input-variant-rel').value = initialValues.variantRel || '';
            rowElement.querySelector('.input-size').value = initialValues.size || '';
            rowElement.querySelector('.input-color').value = initialValues.color || '';
            rowElement.querySelector('.input-best-seller').value = initialValues.bestSeller || 'No';
        }
        
        // Update row number
        clone.querySelector('.row-number').textContent = `#${rowCount}`;
        
        // Setup remove button
        const removeBtn = clone.querySelector('.remove-btn');
        removeBtn.addEventListener('click', () => {
            if (container.children.length > 1) {
                rowElement.remove();
                updateRowNumbers();
            } else {
                alert("You need at least one product row.");
            }
        });

        // Setup copy button
        const copyBtn = clone.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const countStr = prompt("How many copies do you want to make?", "1");
                if (countStr === null) return;
                
                const count = parseInt(countStr, 10);
                if (isNaN(count) || count <= 0) {
                    alert("Please enter a valid number.");
                    return;
                }
                
                const currentVals = {
                    sku: rowElement.querySelector('.input-sku').value,
                    businessCat: rowElement.querySelector('.input-business-cat').value,
                    productCat: rowElement.querySelector('.input-product-cat').value,
                    variantRel: rowElement.querySelector('.input-variant-rel').value,
                    size: rowElement.querySelector('.input-size').value,
                    color: rowElement.querySelector('.input-color').value,
                    bestSeller: rowElement.querySelector('.input-best-seller').value
                };
                
                for (let i = 0; i < count; i++) {
                    addRow(currentVals);
                }
            });
        }

        container.appendChild(clone);
    }

    function updateRowNumbers() {
        const rows = container.querySelectorAll('.product-row');
        rowCount = 0;
        rows.forEach((row) => {
            rowCount++;
            row.querySelector('.row-number').textContent = `#${rowCount}`;
        });
    }

    async function handleGenerate() {
        const rows = container.querySelectorAll('.product-row');
        const products = [];
        let isValid = true;

        rows.forEach(row => {
            const urlInput = row.querySelector('.input-url');
            const skuInput = row.querySelector('.input-sku');
            const businessCatInput = row.querySelector('.input-business-cat');
            const productCatInput = row.querySelector('.input-product-cat');
            const variantRelInput = row.querySelector('.input-variant-rel');
            const sizeInput = row.querySelector('.input-size');
            const colorInput = row.querySelector('.input-color');
            const bestSellerInput = row.querySelector('.input-best-seller');

            // Basic validation
            if (!urlInput.value) {
                urlInput.style.borderColor = 'var(--danger)';
                isValid = false;
            } else {
                urlInput.style.borderColor = 'var(--border-color)';
            }

            if (!businessCatInput.value) {
                businessCatInput.style.borderColor = 'var(--danger)';
                isValid = false;
            } else {
                businessCatInput.style.borderColor = 'var(--border-color)';
            }

            if (!productCatInput.value) {
                productCatInput.style.borderColor = 'var(--danger)';
                isValid = false;
            } else {
                productCatInput.style.borderColor = 'var(--border-color)';
            }

            products.push({
                url: urlInput.value.trim(),
                custom_sku: skuInput.value.trim(),
                business_category: businessCatInput.value,
                product_category: productCatInput.value.trim(),
                variant_relationship: variantRelInput.value,
                size: sizeInput.value.trim(),
                color_name: colorInput.value.trim(),
                best_seller: bestSellerInput.value
            });
        });

        if (!isValid) {
            alert("Please fill in all required fields (marked with *).");
            return;
        }

        // Set Loading state
        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ products })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate Excel file');
            }

            // Get the blob from the response
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            
            // Show success section
            downloadLink.href = downloadUrl;
            resultsSection.classList.remove('hidden');
            
            // Scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            alert(`Error: ${error.message}`);
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        if (isLoading) {
            generateBtn.disabled = true;
            btnText.classList.add('hidden');
            spinner.classList.remove('hidden');
            resultsSection.classList.add('hidden');
        } else {
            generateBtn.disabled = false;
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    }
});
