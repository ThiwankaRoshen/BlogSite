const BLOG_USER_ID_KEY = 'blog_user_id';
const BLOG_USERNAME_KEY = 'blog_username';
const BLOG_AUTH_TOKEN_KEY = 'blog_auth_token';

function getStoredUser() {
  const userId = localStorage.getItem(BLOG_USER_ID_KEY);
  const username = localStorage.getItem(BLOG_USERNAME_KEY);

  if (!userId) {
    return null;
  }

  return {
    id: Number(userId),
    username: username || 'Reader',
  };
}

function setStoredUser(user) {
  localStorage.setItem(BLOG_USER_ID_KEY, String(user.id));
  if (user.username) {
    localStorage.setItem(BLOG_USERNAME_KEY, user.username);
  }
}

function clearStoredUser() {
  localStorage.removeItem(BLOG_USER_ID_KEY);
  localStorage.removeItem(BLOG_USERNAME_KEY);
}

function setAuthToken(token) {
  if (!token) return;
  localStorage.setItem(BLOG_AUTH_TOKEN_KEY, token);
}

function getAuthToken() {
  return localStorage.getItem(BLOG_AUTH_TOKEN_KEY) || null;
}

function clearAuthToken() {
  localStorage.removeItem(BLOG_AUTH_TOKEN_KEY);
}

async function authFetch(url, opts = {}) {
  const token = getAuthToken();
  const headers = new Headers(opts.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(url, { ...opts, headers });
}

function updateAuthUI() {
  const authStatus = document.getElementById('auth-status');
  const signupButton = document.getElementById('signup-button');
  const logoutButton = document.getElementById('logout-button');
  const loginButton = document.getElementById('login-button');
  const currentUser = getStoredUser();

  if (authStatus) {
    if (currentUser) {
      authStatus.textContent = `Signed in as ${currentUser.username}`;
      authStatus.classList.remove('text-slate-400');
      authStatus.classList.add('text-cyan-200');
    } else {
      authStatus.textContent = 'Join the community';
      authStatus.classList.remove('text-cyan-200');
      authStatus.classList.add('text-slate-400');
    }
  }

  if (signupButton) {
    signupButton.classList.toggle('hidden', Boolean(currentUser));
  }

  if (logoutButton) {
    logoutButton.classList.toggle('hidden', !currentUser);
  }
  if (loginButton) {
    loginButton.classList.toggle('hidden', Boolean(currentUser));
  }
}

function openSignupModal() {
  closeErrorModal();
  const modal = document.getElementById('signup-modal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden');
  }
}

function closeSignupModal() {
  const modal = document.getElementById('signup-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
  }
}

function openLoginModal() {
  closeErrorModal();
  const modal = document.getElementById('login-modal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden');
  }
}

function closeLoginModal() {
  const modal = document.getElementById('login-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
  }
}

function showMessage(message, isError = false) {
  const container = document.getElementById('global-message');
  if (!container) {
    return;
  }

  container.textContent = message;
  container.className = isError
    ? 'fixed bottom-6 right-6 z-40 rounded-full border border-rose-400/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-200 shadow-lg'
    : 'fixed bottom-6 right-6 z-40 rounded-full border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200 shadow-lg';
  container.classList.remove('hidden');

  window.setTimeout(() => {
    container.classList.add('hidden');
  }, 2400);
}

function openErrorModal(message) {
  closeSignupModal();
  const modal = document.getElementById('error-modal');
  const text = document.getElementById('error-modal-message');
  if (!modal || !text) {
    return;
  }

  text.textContent = message;
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  document.body.classList.add('overflow-hidden');
}

function showError(message) {
  openErrorModal(message);
  showMessage(message, true);
}

function extractErrorMessage(data, fallback) {
  const detail = data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }
        if (item && typeof item === 'object') {
          return item.msg || item.message || item.error || JSON.stringify(item);
        }
        return String(item);
      })
      .join(', ');
  }

  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') {
      return detail.message;
    }
    if (typeof detail.msg === 'string') {
      return detail.msg;
    }
    if (typeof detail.error === 'string') {
      return detail.error;
    }
    if (typeof detail.detail === 'string') {
      return detail.detail;
    }
    return JSON.stringify(detail);
  }

  return fallback;
}

async function getResponseErrorMessage(response, fallback) {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const data = await response.json().catch(() => ({}));
    return extractErrorMessage(data, fallback);
  }

  const text = await response.text().catch(() => '');
  return text || fallback;
}

async function authenticateUser(email, password) {
  const body = new URLSearchParams();
  body.set('username', email);
  body.set('password', password);

  const response = await fetch('/api/users/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!response.ok) {
    const message = await getResponseErrorMessage(response, 'Authentication failed.');
    throw new Error(message);
  }

  const data = await response.json();
  const token = data?.access_token;
  if (!token) {
    throw new Error('Authentication did not return a token.');
  }

  setAuthToken(token);

  const meResp = await authFetch('/api/users/me');
  if (!meResp.ok) {
    const message = await getResponseErrorMessage(meResp, 'Unable to fetch user info.');
    throw new Error(message);
  }

  const me = await meResp.json();
  setStoredUser({ id: me.id, username: me.username });
  return me;
}

function closeErrorModal() {
  const modal = document.getElementById('error-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
  }
}

function handleCreatePost() {
  const createPostToggle = document.getElementById('create-post-toggle');
  const createPostForm = document.getElementById('create-post-form');
  const cancelCreatePost = document.getElementById('cancel-create-post');
  const titleInput = document.getElementById('new-post-title');
  const contentInput = document.getElementById('new-post-content');

  const currentUser = getStoredUser();
  if (createPostToggle) {
    createPostToggle.classList.toggle('hidden', !currentUser);
  }

  createPostToggle?.addEventListener('click', () => {
    createPostForm?.classList.remove('hidden');
  });

  cancelCreatePost?.addEventListener('click', () => {
    createPostForm?.classList.add('hidden');
    createPostForm?.reset();
  });

  createPostForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const currentUser = getStoredUser();
    if (!currentUser) {
      showError('Please sign up before creating a post.');
      return;
    }

    const payload = {
      title: titleInput?.value.trim() || '',
      content: contentInput?.value.trim() || '',
      user_id: currentUser.id,
    };

    if (!payload.title || !payload.content) {
      showError('Please add both a title and content.');
      return;
    }

    try {
      const response = await authFetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const message = await getResponseErrorMessage(response, 'Unable to create this post.');
        throw new Error(message);
      }

      createPostForm.reset();
      createPostForm.classList.add('hidden');
      showMessage('Post published successfully.');
      window.location.reload();
    } catch (error) {
      showError(error.message);
    }
  });
}

function handlePostActions() {
  const postPage = document.getElementById('post-page');
  if (!postPage) {
    return;
  }

  const postId = postPage.dataset.postId;
  const ownerId = postPage.dataset.ownerId;
  const currentUser = getStoredUser();
  const managementPanel = document.getElementById('post-management');
  const editButton = document.getElementById('edit-post-button');
  const deleteButton = document.getElementById('delete-post-button');
  const editForm = document.getElementById('edit-post-form');
  const cancelButton = document.getElementById('cancel-edit-post');
  const titleInput = document.getElementById('edit-post-title');
  const contentInput = document.getElementById('edit-post-content');
  const postTitle = document.getElementById('post-title');
  const postContent = document.getElementById('post-content');
  const actionStatus = document.getElementById('post-action-status');

  if (managementPanel) {
    const canManage = Boolean(currentUser && Number(currentUser.id) === Number(ownerId));
    managementPanel.classList.toggle('hidden', !canManage);
  }

  editButton?.addEventListener('click', () => {
    if (!editForm) {
      return;
    }

    editForm.classList.remove('hidden');
    if (titleInput && postTitle) {
      titleInput.value = postTitle.textContent.trim();
    }
    if (contentInput && postContent) {
      contentInput.value = postContent.textContent.trim();
    }
  });

  cancelButton?.addEventListener('click', () => {
    editForm?.classList.add('hidden');
  });

  editForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!postId) {
      return;
    }

    const payload = {
      title: titleInput?.value.trim() || '',
      content: contentInput?.value.trim() || '',
    };

    try {
      const response = await authFetch(`/api/posts/${postId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const message = await getResponseErrorMessage(response, 'Unable to update this post.');
        throw new Error(message);
      }

      const updatedPost = await response.json();
      if (postTitle) {
        postTitle.textContent = updatedPost.title;
      }
      if (postContent) {
        postContent.textContent = updatedPost.content;
      }
      if (actionStatus) {
        actionStatus.textContent = 'Post updated successfully.';
      }
      editForm.classList.add('hidden');
      showMessage('Post updated successfully.');
    } catch (error) {
      if (actionStatus) {
        actionStatus.textContent = error.message;
      }
      showError(error.message);
    }
  });

  deleteButton?.addEventListener('click', async () => {
    if (!postId || !window.confirm('Delete this post?')) {
      return;
    }

    try {
      const response = await authFetch(`/api/posts/${postId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const message = await getResponseErrorMessage(response, 'Unable to delete this post.');
        throw new Error(message);
      }

      window.location.href = '/';
    } catch (error) {
      if (actionStatus) {
        actionStatus.textContent = error.message;
      }
      showError(error.message);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  handleCreatePost();
  handlePostActions();

  const signupButton = document.getElementById('signup-button');
  const logoutButton = document.getElementById('logout-button');
  const signupModal = document.getElementById('signup-modal');
  const closeButton = document.getElementById('close-signup-modal');
  const signupForm = document.getElementById('signup-form');
  const errorModal = document.getElementById('error-modal');
  const closeErrorButton = document.getElementById('close-error-modal');

  signupButton?.addEventListener('click', openSignupModal);
  logoutButton?.addEventListener('click', () => {
    clearStoredUser();
    clearAuthToken();
    updateAuthUI();
    showMessage('You have been logged out.');
  });

  const loginButton = document.getElementById('login-button');
  const loginModal = document.getElementById('login-modal');
  const closeLoginButton = document.getElementById('close-login-modal');
  const loginForm = document.getElementById('login-form');

  loginButton?.addEventListener('click', openLoginModal);
  closeLoginButton?.addEventListener('click', closeLoginModal);
  loginModal?.addEventListener('click', (event) => {
    if (event.target === loginModal) {
      closeLoginModal();
    }
  });

  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    const email = String(formData.get('email') || '').trim();
    const password = String(formData.get('password') || '');

    if (!email || !password) {
      showError('Please provide both email and password.');
      return;
    }

    try {
      const me = await authenticateUser(email, password);
      updateAuthUI();
      closeLoginModal();
      showMessage(`Welcome back, ${me.username}!`);
    } catch (error) {
      showError(error.message);
    }
  });

  closeButton?.addEventListener('click', closeSignupModal);
  signupModal?.addEventListener('click', (event) => {
    if (event.target === signupModal) {
      closeSignupModal();
    }
  });
  closeErrorButton?.addEventListener('click', closeErrorModal);
  errorModal?.addEventListener('click', (event) => {
    if (event.target === errorModal) {
      closeErrorModal();
    }
  });

  signupForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const usernameInput = document.getElementById('signup-username');
    const emailInput = document.getElementById('signup-email');
    const passwordInput = document.getElementById('signup-password');

    const payload = {
      username: String(usernameInput?.value || '').trim(),
      email: String(emailInput?.value || '').trim(),
      password: String(passwordInput?.value || ''),
    };

    if (!payload.username || !payload.email || !payload.password) {
      showError('Please provide a username, email, and password.');
      return;
    }

    if (payload.password.length < 8) {
      showError('Password must be at least 8 characters long.');
      return;
    }

    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const message = await getResponseErrorMessage(response, 'Signup failed.');
        throw new Error(message);
      }

      const createdUser = await response.json();
      const me = await authenticateUser(payload.email, payload.password);
      updateAuthUI();
      signupForm.reset();
      closeSignupModal();
      showMessage(`Welcome, ${me.username || createdUser.username}!`);
    } catch (error) {
      showError(error.message);
    }
  });
});
