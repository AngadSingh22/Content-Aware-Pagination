
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-upload');
const previewContainer = document.getElementById('preview-container');
const imagePreview = document.getElementById('image-preview');
const fileName = document.getElementById('file-name');
const processBtn = document.getElementById('process-btn');
const formatSelect = document.getElementById('format-select');
const customSizeGroup = document.getElementById('custom-size-group');
const statusArea = document.getElementById('status-area');
const statusText = document.getElementById('status-text');
const resultsArea = document.getElementById('results-area');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropZone.classList.add('dragover');
}

function unhighlight(e) {
    dropZone.classList.remove('dragover');
}

dropZone.addEventListener('drop', handleDrop, false);
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                fileName.textContent = file.name;
                previewContainer.classList.remove('hidden');
                document.querySelector('.upload-label').classList.add('hidden');
                processBtn.disabled = false;
                
                window.uploadedFile = file;
                window.uploadedFileBytes = new Uint8Array(e.target.result); 
            }
            reader.readAsArrayBuffer(file); 
            
            const urlReader = new FileReader();
            urlReader.onload = function(e) {
                imagePreview.src = e.target.result;
            }
            urlReader.readAsDataURL(file);
        }
    }
}

formatSelect.addEventListener('change', (e) => {
    if (e.target.value === 'CUSTOM') {
        customSizeGroup.classList.remove('hidden');
    } else {
        customSizeGroup.classList.add('hidden');
    }
});


processBtn.addEventListener('click', async () => {
    resultsArea.classList.add('hidden');
    statusArea.classList.remove('hidden');
    statusText.textContent = "Processing... This may take a moment.";
    processBtn.disabled = true;

    try {
        
        await new Promise(r => setTimeout(r, 100)); 
        
        const pyscriptBtn = document.getElementById('run-python-logic');
        if (pyscriptBtn) {
            pyscriptBtn.click();
        } else {
            
            const event = new CustomEvent('process-trigger');
            window.dispatchEvent(event);
        }
    } catch (e) {
        console.error(e);
        statusText.textContent = "Error: " + e.message;
    }
});

window.processingComplete = function(downloadUrl, filename) {
    statusArea.classList.add('hidden');
    resultsArea.classList.remove('hidden');
    processBtn.disabled = false;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    link.className = 'primary-btn';
    link.textContent = 'Download PDF';
    link.style.display = 'block';
    link.style.marginTop = '1rem';
    link.style.textAlign = 'center';
    link.style.textDecoration = 'none';

    const container = document.getElementById('download-links');
    container.innerHTML = '';
    container.appendChild(link);
}
