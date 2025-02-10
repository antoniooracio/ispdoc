document.addEventListener("DOMContentLoaded", function() {
    const empresaField = document.querySelector("#id_empresa");
    const parentField = document.querySelector("#id_parent");

    function atualizarParent() {
        const empresaId = empresaField.value;
        if (!empresaId) {
            parentField.innerHTML = '<option value="">---------</option>';
            return;
        }

        fetch(`/admin/get_parents/?empresa_id=${empresaId}`)
            .then(response => response.json())
            .then(data => {
                parentField.innerHTML = '<option value="">---------</option>'; // Reseta o campo Parent
                data.forEach(bloco => {
                    const option = document.createElement("option");
                    option.value = bloco.id;
                    option.textContent = bloco.bloco_cidr;
                    parentField.appendChild(option);
                });
            })
            .catch(error => console.error("Erro ao buscar blocos de IP:", error));
    }

    if (empresaField) {
        empresaField.addEventListener("change", atualizarParent);
    }
});
