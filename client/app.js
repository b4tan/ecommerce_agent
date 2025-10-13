const API = localStorage.getItem("API_BASE") || "http://localhost:8001";
const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const imagePreview = document.getElementById("image-preview");
const previewImg = document.getElementById("preview-img");
let currentFile = null;

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file && file.type.startsWith('image/')) {
    currentFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      imagePreview.classList.add('show');
    };
    reader.readAsDataURL(file);
  }
}

function removeImage() {
  currentFile = null;
  imagePreview.classList.remove('show');
  previewImg.src = '';
  document.getElementById('file-input').value = '';
}

function addMessage(text, isUser, products = null, timestamp = null) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
  
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = isUser ? '👤' : '🤖';
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = text;
  
  const time = document.createElement('div');
  time.className = 'message-time';
  time.textContent = timestamp || new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  contentDiv.appendChild(bubble);
  
  // Only add products if they exist and are not null/empty
  if (products && Array.isArray(products) && products.length > 0) {
    const productsGrid = createProductsGrid(products);
    contentDiv.appendChild(productsGrid);
  }
  
  contentDiv.appendChild(time);
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(contentDiv);
  messagesDiv.appendChild(messageDiv);
  
  scrollToBottom();
  return messageDiv;
}

function createProductsGrid(products) {
  const grid = document.createElement('div');
  grid.className = 'products-grid';
  
  products.forEach(product => {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.onclick = () => window.open(product.url, '_blank');
    
    const img = document.createElement('img');
    img.src = product.image_url || '';
    img.alt = product.title || '';
    
    const title = document.createElement('div');
    title.className = 'product-title';
    title.textContent = product.title || 'No title';
    
    const meta = document.createElement('div');
    meta.className = 'product-meta';
    
    const price = document.createElement('div');
    price.className = 'product-price';
    if (product.final_price != null && product.final_price > 0) {
      price.textContent = `$${product.final_price.toFixed(2)}`;
    } else {
      price.textContent = 'See price';
      price.style.fontSize = '11px';
      price.style.color = '#86868b';
    }
    
    const rating = document.createElement('div');
    rating.className = 'product-rating';
    rating.textContent = product.rating != null 
      ? `⭐ ${product.rating.toFixed(1)}`
      : '⭐ N/A';
    
    meta.appendChild(price);
    meta.appendChild(rating);
    
    card.appendChild(img);
    card.appendChild(title);
    card.appendChild(meta);
    
    grid.appendChild(card);
  });
  
  return grid;
}

function showTyping() {
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message bot';
  typingDiv.id = 'typing-indicator';
  
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = '🤖';
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.innerHTML = '<span></span><span></span><span></span>';
  
  contentDiv.appendChild(typing);
  typingDiv.appendChild(avatar);
  typingDiv.appendChild(contentDiv);
  messagesDiv.appendChild(typingDiv);
  
  scrollToBottom();
}

function hideTyping() {
  const typing = document.getElementById('typing-indicator');
  if (typing) typing.remove();
}

function scrollToBottom() {
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
  const text = messageInput.value.trim();
  
  if (!text && !currentFile) return;
  
  // Disable input while processing
  sendBtn.disabled = true;
  messageInput.disabled = true;
  
  // Add user message
  if (text) {
    addMessage(text, true);
  }
  if (currentFile) {
    addMessage(`📎 Image attached`, true);
  }
  
  // Clear input
  messageInput.value = '';
  messageInput.style.height = 'auto';
  
  // Show typing indicator
  showTyping();
  
  try {
    let response;
    
    if (currentFile) {
      // Send with image
      const formData = new FormData();
      formData.append('file', currentFile);
      formData.append('query', text || '');
      
      // Debug logging
      console.log('File details:', {
        name: currentFile.name,
        type: currentFile.type,
        size: currentFile.size
      });
      
      const res = await fetch(`${API}/chat/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      response = await res.json();
    } else {
      // Send text only
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      response = await res.json();
    }
    
    hideTyping();
    
    // Add bot response
    const botText = response.response || "I found some products for you!";
    const products = response.products || null;
    
    // Debug logging
    console.log('API Response:', response);
    console.log('Products to show:', products);
    
    addMessage(botText, false, products);
    
    // Remove image after successful processing
    if (currentFile) {
      removeImage();
    }
    
  } catch (error) {
    hideTyping();
    addMessage(`Sorry, I encountered an error: ${error.message}. Please try again.`, false);
    console.error('Error:', error);
  } finally {
    // Re-enable input
    sendBtn.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
  }
}

// Focus input on load
messageInput.focus();
