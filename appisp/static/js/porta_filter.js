(function($) {
    $(document).ready(function() {
        $('#id_equipamento_conexao').change(function() {
            var equipamentoConexao = $(this).val();
            var conexaoField = $('#id_conexao');

            conexaoField.val(null).trigger('change'); // Reseta o campo de conexão
            conexaoField.select2({
                ajax: {
                    url: conexaoField.data('autocomplete-url'),
                    data: function(params) {
                        return {
                            q: params.term,
                            equipamento_conexao: equipamentoConexao  // 🔥 Nome correto aqui!
                        };
                    }
                }
            });
        });
    });
})(django.jQuery);
