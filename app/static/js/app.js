// Stan globalny aplikacji
let userSubscription = "active";
let queriesList = [];

// Elementy DOM
const authForm = document.getElementById("auth-form");
const authEmail = document.getElementById("auth-email");
const authPassword = document.getElementById("auth-password");
const btnLogin = document.getElementById("btn-login");
const btnSignup = document.getElementById("btn-signup");
const authMessage = document.getElementById("auth-message");

const btnLogout = document.getElementById("btn-logout");
const btnRefresh = document.getElementById("btn-refresh");
const btnBilling = document.getElementById("btn-billing");
const btnStripeAction = document.getElementById("btn-stripe-action");
const btnCopyEmail = document.getElementById("btn-copy-email");

const inboundEmailInput = document.getElementById("inbound-email-address");
const queriesTableBody = document.getElementById("queries-table-body");
const noQueriesAlert = document.getElementById("no-queries-alert");

// Modale
const modalDetails = document.getElementById("modal-details");
const modalSimulator = document.getElementById("modal-simulator");
const btnOpenSimulator = document.getElementById("btn-open-simulator");
const simulatorForm = document.getElementById("simulator-form");
const btnLoadSample = document.getElementById("btn-load-sample");

// --- Obsługa powiadomień TOAST ---
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    
    const colors = {
        success: "bg-emerald-950 border-emerald-800 text-emerald-300",
        error: "bg-red-950 border-red-800 text-red-300",
        warning: "bg-amber-950 border-amber-800 text-amber-300",
        info: "bg-indigo-950 border-indigo-800 text-indigo-300"
    };
    
    const icons = {
        success: "fa-circle-check",
        error: "fa-triangle-exclamation",
        warning: "fa-circle-exclamation",
        info: "fa-circle-info"
    };

    toast.className = `p-4 rounded-xl border flex items-center gap-3 shadow-xl transition-all duration-300 transform translate-y-2 opacity-0 max-w-sm ${colors[type]}`;
    toast.innerHTML = `
        <i class="fa-solid ${icons[type]} text-lg"></i>
        <div class="text-xs font-medium">${message}</div>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    }, 10);
    
    // Remove after 4s
    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-[-10px]");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Obsługa logowania / rejestracji ---
if (authForm) {
    authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
    });

    btnLogin.addEventListener("click", async () => {
        const email = authEmail.value.trim();
        const password = authPassword.value.trim();
        if (!email || !password) return;
        
        authMessage.classList.add("hidden");
        
        if (window.isMockMode) {
            // Mock Mode logowanie
            localStorage.setItem("lojiparse_mock_email", email);
            showToast("Zalogowano pomyślnie (Tryb Testowy / Mock)", "success");
            setupMockAuth();
        } else {
            // Logowanie Supabase
            const { data, error } = await window.supabaseClient.auth.signInWithPassword({ email, password });
            if (error) {
                authMessage.textContent = `Błąd logowania: ${error.message}`;
                authMessage.className = "mt-4 p-3 rounded-lg text-xs text-center bg-red-950/40 border border-red-900/40 text-red-300";
                authMessage.classList.remove("hidden");
            } else {
                showToast("Zalogowano pomyślnie", "success");
            }
        }
    });

    btnSignup.addEventListener("click", async () => {
        const email = authEmail.value.trim();
        const password = authPassword.value.trim();
        if (!email || !password) return;
        
        authMessage.classList.add("hidden");
        
        if (window.isMockMode) {
            // Mock Mode rejestracja
            localStorage.setItem("lojiparse_mock_email", email);
            showToast("Zarejestrowano pomyślnie (Tryb Testowy / Mock)", "success");
            setupMockAuth();
        } else {
            // Rejestracja Supabase
            const { data, error } = await window.supabaseClient.auth.signUp({ email, password });
            if (error) {
                authMessage.textContent = `Błąd rejestracji: ${error.message}`;
                authMessage.className = "mt-4 p-3 rounded-lg text-xs text-center bg-red-950/40 border border-red-900/40 text-red-300";
                authMessage.classList.remove("hidden");
            } else {
                authMessage.textContent = "Konto zostało utworzone. Sprawdź e-mail w celu weryfikacji lub spróbuj się zalogować.";
                authMessage.className = "mt-4 p-3 rounded-lg text-xs text-center bg-indigo-950/40 border border-indigo-900/40 text-indigo-300";
                authMessage.classList.remove("hidden");
                showToast("Utworzono konto pomyślnie", "success");
            }
        }
    });
}

// Obsługa wylogowania
if (btnLogout) {
    btnLogout.addEventListener("click", async () => {
        if (window.isMockMode) {
            localStorage.removeItem("lojiparse_mock_email");
            window.currentSession = null;
            window.location.reload();
        } else {
            await window.supabaseClient.auth.signOut();
            showToast("Wylogowano użytkownika", "info");
        }
    });
}

// --- Pobieranie i renderowanie danych ---
window.loadDashboardData = async function() {
    if (!window.currentSession) return;
    
    const userId = window.isMockMode ? window.MOCK_USER_ID : window.currentSession.user.id;
    
    // Ustalamy adres e-mail skrzynki inbound
    inboundEmailInput.value = `inbound-${userId}@lojiparse.com`;
    
    await fetchSubscriptionStatus();
    await fetchQueriesList();
};

async function fetchSubscriptionStatus() {
    try {
        const response = await authenticatedFetch("/api/v1/queries/billing-portal", { method: "POST" });
        const data = await response.json();
    } catch (e) {
        console.error("Błąd pobierania subskrypcji:", e);
    }
}

async function fetchQueriesList() {
    try {
        const response = await authenticatedFetch("/api/v1/queries");
        if (response.status === 401) {
            return;
        }
        
        queriesList = await response.json();
        renderQueriesTable();
        updateSubscriptionUI();
    } catch (error) {
        console.error("Błąd pobierania zapytań:", error);
        showToast("Nie udało się załadować listy zapytań.", "error");
    }
}

function updateSubscriptionUI() {
    userSubscription = "active";
}

function renderQueriesTable() {
    queriesTableBody.innerHTML = "";
    
    if (queriesList.length === 0) {
        noQueriesAlert.classList.remove("hidden");
        return;
    }
    
    noQueriesAlert.classList.add("hidden");
    
    queriesList.forEach(query => {
        const row = document.createElement("tr");
        row.className = "hover:bg-slate-800/20 transition cursor-pointer glass-card-hover";
        row.dataset.id = query.id;
        
        let statusBadge = "";
        if (query.status === "parsed") {
            statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-950 border border-emerald-800 text-emerald-400"><i class="fa-solid fa-check text-[10px]"></i> Sparsowano</span>`;
        } else if (query.status === "parsing") {
            statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950 border border-amber-800 text-amber-400"><i class="fa-solid fa-spinner fa-spin text-[10px]"></i> Parsowanie...</span>`;
        } else if (query.status === "failed") {
            statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-950 border border-red-800 text-red-400"><i class="fa-solid fa-xmark text-[10px]"></i> Błąd</span>`;
        } else {
            statusBadge = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-950 border border-indigo-800 text-indigo-400"><i class="fa-solid fa-envelope text-[10px]"></i> Otrzymano</span>`;
        }
        
        let route = "Brak danych";
        if (query.parsed_data && query.parsed_data.origin_city && query.parsed_data.destination_city) {
            route = `${query.parsed_data.origin_city} ➔ ${query.parsed_data.destination_city}`;
        }
        
        const price = query.quote_price ? `${query.quote_price.toFixed(2)} EUR` : "-";
        
        const date = new Date(query.created_at).toLocaleString("pl-PL", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        });
        
        row.innerHTML = `
            <td class="py-4 px-6 font-medium whitespace-nowrap">${statusBadge}</td>
            <td class="py-4 px-6 text-slate-300 truncate max-w-[150px]">${escapeHtml(query.sender)}</td>
            <td class="py-4 px-6 text-slate-200 truncate max-w-[200px]">${escapeHtml(query.subject || "Brak tematu")}</td>
            <td class="py-4 px-6 text-indigo-300 font-semibold">${escapeHtml(route)}</td>
            <td class="py-4 px-6 text-emerald-400 font-extrabold">${price}</td>
            <td class="py-4 px-6 text-slate-400 text-xs">${date}</td>
            <td class="py-4 px-6 text-right">
                <div class="flex gap-2 justify-end">
                    <button class="btn-view-details text-xs bg-slate-800 hover:bg-slate-700 text-indigo-400 py-1.5 px-3 rounded-lg border border-slate-700/60 transition flex items-center gap-1">
                        <i class="fa-solid fa-eye"></i> Szczegóły
                    </button>
                    <button class="btn-download-pdf text-xs ${query.status === 'parsed' ? 'bg-indigo-600/80 hover:bg-indigo-600 text-white' : 'bg-slate-800 text-slate-500 cursor-not-allowed'} py-1.5 px-3 rounded-lg transition flex items-center gap-1" ${query.status === 'parsed' ? '' : 'disabled'}>
                        <i class="fa-solid fa-file-pdf"></i> PDF
                    </button>
                </div>
            </td>
        `;
        
        row.querySelector(".btn-view-details").addEventListener("click", (e) => {
            e.stopPropagation();
            openDetailsModal(query.id);
        });
        
        row.querySelector(".btn-download-pdf").addEventListener("click", (e) => {
            e.stopPropagation();
            downloadPdf(query.id);
        });
        
        row.addEventListener("click", () => {
            openDetailsModal(query.id);
        });
        
        queriesTableBody.appendChild(row);
    });
}

function escapeHtml(text) {
    if (!text) return "";
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

let currentModalQueryId = null;

async function openDetailsModal(queryId) {
    currentModalQueryId = queryId;
    
    try {
        const response = await authenticatedFetch(`/api/v1/queries/${queryId}`);
        const query = await response.json();
        
        document.getElementById("detail-modal-title").textContent = query.subject || "Zapytanie Logistyczne";
        document.getElementById("detail-modal-sender").innerHTML = `<b>Nadawca:</b> ${escapeHtml(query.sender)} | <b>Odbiorca:</b> ${escapeHtml(query.recipient)}`;
        
        const badge = document.getElementById("detail-status-badge");
        badge.textContent = query.status.toUpperCase();
        if (query.status === "parsed") {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-950 border border-emerald-800 text-emerald-400";
            document.getElementById("detail-price-text").textContent = query.quote_price ? `${query.quote_price.toFixed(2)} EUR` : "-";
            document.getElementById("btn-download-pdf-modal").disabled = false;
            document.getElementById("btn-download-pdf-modal").className = "bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 px-5 rounded-xl transition text-sm flex items-center gap-2 shadow-lg shadow-indigo-600/10";
        } else if (query.status === "parsing") {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950 border border-amber-800 text-amber-400";
            document.getElementById("detail-price-text").textContent = "Parsowanie...";
            document.getElementById("btn-download-pdf-modal").disabled = true;
            document.getElementById("btn-download-pdf-modal").className = "bg-slate-800 text-slate-500 cursor-not-allowed py-2 px-5 rounded-xl text-sm flex items-center gap-2";
        } else if (query.status === "failed") {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-950 border border-red-800 text-red-400";
            document.getElementById("detail-price-text").textContent = "Błąd parsowania";
            document.getElementById("btn-download-pdf-modal").disabled = true;
            document.getElementById("btn-download-pdf-modal").className = "bg-slate-800 text-slate-500 cursor-not-allowed py-2 px-5 rounded-xl text-sm flex items-center gap-2";
        } else {
            badge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-950 border border-indigo-800 text-indigo-400";
            document.getElementById("detail-price-text").textContent = "Oczekiwanie";
            document.getElementById("btn-download-pdf-modal").disabled = true;
            document.getElementById("btn-download-pdf-modal").className = "bg-slate-800 text-slate-500 cursor-not-allowed py-2 px-5 rounded-xl text-sm flex items-center gap-2";
        }
        
        const parsed = query.parsed_data || {};
        const origin = `${parsed.origin_city || "-"} ${parsed.origin_postcode ? `(${parsed.origin_postcode})` : ""}`;
        const destination = `${parsed.destination_city || "-"} ${parsed.destination_postcode ? `(${parsed.destination_postcode})` : ""}`;
        const dist = parsed.estimated_distance_km ? `${parsed.estimated_distance_km} km` : "-";
        
        document.getElementById("detail-route-text").textContent = `${origin} ➔ ${destination} (${dist})`;
        document.getElementById("detail-weight-text").textContent = parsed.total_weight_kg ? `${parsed.total_weight_kg} kg` : "-";
        document.getElementById("detail-volume-text").textContent = parsed.total_volume_cbm ? `${parsed.total_volume_cbm} CBM` : "-";
        document.getElementById("detail-instructions-text").textContent = parsed.handling_instructions || "Brak instrukcji specjalnych";
        
        document.getElementById("detail-original-body").textContent = query.body;
        
        const cargoTbody = document.getElementById("detail-cargo-tbody");
        cargoTbody.innerHTML = "";
        
        const items = parsed.cargo_items || [];
        if (items.length === 0) {
            cargoTbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-500 italic">Brak wyszczególnionych pozycji towarowych</td></tr>`;
        } else {
            items.forEach(item => {
                const tr = document.createElement("tr");
                const dims = (item.length_cm && item.width_cm && item.height_cm) 
                    ? `${item.length_cm}x${item.width_cm}x${item.height_cm}` 
                    : "-";
                
                tr.innerHTML = `
                    <td class="py-2 px-3">${escapeHtml(item.description)}</td>
                    <td class="py-2 px-3 text-center font-bold text-indigo-400">${item.pieces || "-"}</td>
                    <td class="py-2 px-3">${item.weight_kg ? `${item.weight_kg} kg` : "-"}</td>
                    <td class="py-2 px-3 font-mono text-slate-400">${dims}</td>
                `;
                cargoTbody.appendChild(tr);
            });
        }
        
        modalDetails.classList.remove("hidden");
        
    } catch (e) {
        console.error("Błąd ładowania szczegółów:", e);
        showToast("Nie udało się pobrać szczegółów zapytania.", "error");
    }
}

async function downloadPdf(queryId) {
    
    showToast("Generowanie wyceny PDF...", "info");
    
    try {
        const response = await authenticatedFetch(`/api/v1/queries/${queryId}/pdf?t=${Date.now()}`);
        

        
        if (!response.ok) {
            throw new Error("HTTP error generating PDF");
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = `Wycena_LojiParse_${queryId.slice(0, 8).toUpperCase()}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        showToast("Pobrano plik PDF.", "success");
    } catch (error) {
        console.error("Błąd pobierania PDF:", error);
        showToast("Wystąpił błąd podczas generowania pliku PDF.", "error");
    }
}

document.getElementById("btn-download-pdf-modal").addEventListener("click", () => {
    if (currentModalQueryId) {
        downloadPdf(currentModalQueryId);
    }
});

document.querySelectorAll(".modal-close-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        modalDetails.classList.add("hidden");
    });
});

window.addEventListener("click", (e) => {
    if (e.target === modalDetails) {
        modalDetails.classList.add("hidden");
    }
    if (e.target === modalSimulator) {
        modalSimulator.classList.add("hidden");
    }
});

if (btnBilling) {
    btnBilling.addEventListener("click", redirectToStripe);
}
if (btnStripeAction) {
    btnStripeAction.addEventListener("click", redirectToStripe);
}

async function redirectToStripe() {
    showToast("Przekierowywanie do Stripe...", "info");
    try {
        const response = await authenticatedFetch("/api/v1/queries/billing-portal", { method: "POST" });
        const data = await response.json();
        
        if (data.url) {
            window.open(data.url, "_blank");
        } else {
            throw new Error("Brak URL płatności");
        }
    } catch (e) {
        console.error("Błąd Stripe:", e);
        showToast("Nie udało się otworzyć płatności Stripe.", "error");
    }
}

btnCopyEmail.addEventListener("click", () => {
    inboundEmailInput.select();
    inboundEmailInput.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(inboundEmailInput.value);
    showToast("Skopiowano adres e-mail do schowka!", "success");
});

// --- Symulator Mailgun (Wysyłanie testowych webhooków) ---
if (btnOpenSimulator) {
    btnOpenSimulator.addEventListener("click", () => {
        modalSimulator.classList.remove("hidden");
    });
}

document.getElementById("simulator-close-btn").addEventListener("click", () => {
    modalSimulator.classList.add("hidden");
});

document.getElementById("simulator-cancel-btn").addEventListener("click", () => {
    modalSimulator.classList.add("hidden");
});

const SAMPLES = {
    standard: `Szanowni Państwo,
    
Proszę o wycenę transportu drogowego na trasie Warszawa (kod pocztowy 02-222) do Frankfurt nad Menem (kod pocztowy 60311), Niemcy.
Do przewiezienia mamy:
- 3 palety Euro z elektroniką, waga jednej palety to 350 kg, wysokość 160 cm.
- 1 skrzynię drewnianą o wymiarach 120x80x100 cm, waga 450 kg.

Łączna waga to około 1500 kg. Towar jest gotowy do załadunku od jutra od rana.
Proszę o informację o cenie oraz możliwym terminie dostawy.

Z poważaniem,
Tomasz Kowalski
Logistics Manager`,
};

if (btnLoadSample) {
    btnLoadSample.addEventListener("click", () => {
        document.getElementById("sim-body").value = SAMPLES.standard;
    });
}

document.getElementById("sim-body").value = SAMPLES.standard;

simulatorForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const sender = document.getElementById("sim-sender").value.trim();
    const subject = document.getElementById("sim-subject").value.trim();
    const body = document.getElementById("sim-body").value.trim();
    
    const userId = window.isMockMode ? window.MOCK_USER_ID : window.currentSession.user.id;
    const recipient = `inbound-${userId}@lojiparse.com`;
    
    showToast("Wysyłanie testowego e-maila...", "info");
    
    try {
        const payload = {
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "body-plain": body,
            "timestamp": Math.floor(Date.now() / 1000).toString(),
            "token": "test-mock-token-" + Math.random().toString(36).substr(2, 9),
            "signature": "test-mock-signature"
        };
        
        const response = await fetch("/api/v1/webhook/incoming-mail", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast("Webhook wysłany! Rozpoczęto parsowanie.", "success");
            modalSimulator.classList.add("hidden");
            setTimeout(fetchQueriesList, 1500);
        } else {
            showToast(`Błąd: ${result.detail || "Nieznany błąd"}`, "error");
        }
    } catch (error) {
        console.error("Błąd wysyłania webhooka:", error);
        showToast("Nie udało się połączyć z API webhooka.", "error");
    }
});

btnRefresh.addEventListener("click", () => {
    showToast("Odświeżanie zapytań...", "info");
    fetchQueriesList();
});

setInterval(() => {
    if (window.currentSession) {
        fetchQueriesList();
    }
}, 10000);


