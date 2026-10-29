// Inicjalizacja klienta Supabase i sesji na obiekcie window dla pełnej kompatybilności między plikami
window.supabaseClient = null;
window.currentSession = null;
window.isMockMode = false;
window.MOCK_USER_ID = "98bc203e-d9a2-4a0b-90f7-111fbfa251bd";

// Konfigurowanie konfiguracji publicznej z backendu
async function initializeAuth() {
    try {
        const response = await fetch('/api/v1/config');
        const config = await response.json();
        

        
        // Zawsze logujemy w trybie mock i pomijamy ekran logowania
        setupMockAuth();
        
    } catch (error) {
        console.error("Error initializing Auth, falling back to mock mode:", error);
        setupMockAuth();
    }
}

// Funkcja obsługująca zmianę stanu zalogowania
function handleAuthStateChange(session) {
    const dashboardContainer = document.getElementById("dashboard-container");
    const userEmailDisplay = document.getElementById("user-email-display");
    
    if (dashboardContainer) dashboardContainer.classList.remove("hidden");
    if (session && userEmailDisplay) userEmailDisplay.textContent = session.user.email;
    
    // Załaduj dane do dashboardu
    if (window.loadDashboardData) {
        window.loadDashboardData();
    }
}

// --- Obsługa Mock Auth na potrzeby lokalnego testowania ---
function setupMockAuth() {
    window.isMockMode = true;
    console.info("Mock Auth active. Auto-login enabled.");
    
    const mockSession = {
        access_token: "mock-jwt-token-active",
        user: { id: window.MOCK_USER_ID, email: "user@lojiparse.com" }
    };
    window.currentSession = mockSession;
    handleAuthStateChange(mockSession);
}

// Funkcje pomocnicze do wstrzykiwania nagłówków autoryzacji
async function authenticatedFetch(url, options = {}) {
    if (!options.headers) {
        options.headers = {};
    }
    
    let token = "";
    if (window.isMockMode) {
        token = "mock-jwt-token-active";
    } else if (window.currentSession) {
        token = window.currentSession.access_token;
    }
    
    options.headers["Authorization"] = `Bearer ${token}`;
    return fetch(url, options);
}

// Uruchomienie inicjalizacji po załadowaniu drzewa DOM
document.addEventListener("DOMContentLoaded", () => {
    initializeAuth();
});
