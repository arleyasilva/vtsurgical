// ===================================================
// Função para enviar dados via AJAX para o servidor
// ===================================================
function sendConfig(action, formData) {
    const alertBox = document.getElementById('alert-box') || document.getElementById('statusMsg') || document.getElementById('restart-message');
    alertBox.innerHTML = '';

    fetch('/config', { 
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alertBox.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
        } 
        else if (data.status === 'restarting') {
            alertBox.innerHTML = `
                <div class="alert alert-info">
                    <strong>Salvando configurações...</strong><br>
                    Reiniciando servidor, aguarde...
                </div>
            `;
            iniciarContagemReinicio(alertBox);
        } 
        else {
            alertBox.innerHTML = `<div class="alert alert-error">${data.message}</div>`;
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alertBox.innerHTML = `<div class="alert alert-error">Erro ao processar a requisição: ${error.message || 'Erro de conexão ou servidor.'}</div>`;
    });
}

// ===================================================
// Função de Contagem de Reinício (3...2...1...)
// ===================================================
function iniciarContagemReinicio(alertBox) {
    let contagem = 3;
    alertBox.innerHTML = `<div class="alert alert-info">🔁 Reiniciando servidor em ${contagem}...</div>`;
    const intervalo = setInterval(() => {
        contagem--;
        if (contagem >= 0) {
            alertBox.innerHTML = `<div class="alert alert-info">🔁 Reiniciando servidor em ${contagem}...</div>`;
        } else {
            clearInterval(intervalo);
            alertBox.innerHTML = `<div class="alert alert-success">✅ Servidor reiniciado!</div>`;
            setTimeout(() => {
                // Tenta reconectar automaticamente
                const currentPort = window.location.port;
                const newPort = currentPort === "5001" ? "5002" : "5001";
                const newUrl = `${window.location.protocol}//${window.location.hostname}:${newPort}`;
                window.location.href = newUrl;
            }, 1000);
        }
    }, 1000);
}

// ===================================================
// EVENTOS PRINCIPAIS
// ===================================================
document.addEventListener('DOMContentLoaded', () => {

    // === Salvar e Reiniciar ===
    const globalConfigForm = document.getElementById('global-config-form') || document.getElementById('configForm');
    if (globalConfigForm) {
        globalConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Captura resolução (ex: 1280x720)
            const resolutionSelect = document.getElementById('resolution_select') || document.querySelector('[name="camera_resolution"]');
            if (resolutionSelect) {
                const [width, height] = resolutionSelect.value.split('x');
                formData = new FormData(this);
                formData.append('camera_width', width);
                formData.append('camera_height', height);
            } else {
                formData = new FormData(this);
            }

            formData.append('action', 'save_all');
            sendConfig('save_all', formData);
        });
    }

    // === Alterar Senha ===
    const passwordForm = document.getElementById('password-form') || document.getElementById('userForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            formData.append('action', 'update_password');
            sendConfig('update_password', formData);
        });
    }

    // === Adicionar Usuário ===
    const addUserForm = document.getElementById('add-user-form') || document.getElementById('addUserForm');
    if (addUserForm) {
        addUserForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            formData.append('action', 'add_user');
            sendConfig('add_user', formData);
        });
    }

    // === Excluir Usuário ===
    document.querySelectorAll('.btn-delete').forEach(button => {
        button.addEventListener('click', function() {
            const usernameToDelete = this.getAttribute('data-username');
            if (confirm(`Tem certeza que deseja excluir o usuário ${usernameToDelete}?`)) {
                const formData = new FormData();
                formData.append('action', 'delete_user');
                formData.append('username_to_delete', usernameToDelete);
                sendConfig('delete_user', formData);
            }
        });
    });
});
