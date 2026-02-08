// Función para resetear el modal al estado original (Nuevo Gasto)
function prepararNuevoGasto() {
  const form = document.getElementById('formGasto');
  form.reset();
  form.action = urlCrear;
  
  // Resetear títulos y UI
  document.getElementById('modalGastoTitulo').innerText = "Registrar Nuevo Gasto";
  document.getElementById('modalGastoSubtitulo').innerText = "Egreso de Caja";
  document.getElementById('infoTextGasto').innerHTML = "<b>Nota:</b> Si registras una compra desde inventario, el gasto se genera solo.";
  document.getElementById('btnSubmitGasto').innerText = "Confirmar";

  // Habilitar campos
  const inputs = form.querySelectorAll('input, select');
  inputs.forEach(i => {
      i.readOnly = false;
      i.disabled = false;
      i.classList.remove('opacity-50');
  });
  
  abrirModal('modalNuevoGasto');
}

function abrirEditarGasto(id) {
  fetch(`/administrador/gastos/api/${id}/`)
      .then(response => response.json())
      .then(data => {
          const form = document.getElementById('formGasto');
          form.action = `/administrador/gastos/editar/${id}/`;
          
          // Rellenar datos
          form.querySelector('[name="descripcion"]').value = data.descripcion;
          form.querySelector('[name="notas"]').value = data.notas || '';
          form.querySelector('[name="monto"]').value = data.monto;
          form.querySelector('[name="fecha"]').value = data.fecha;
          
          const selectTipo = document.getElementById('selectTipoGasto');
          const infoText = document.getElementById('infoTextGasto');
          const sub = document.getElementById('modalGastoSubtitulo');
          
          selectTipo.value = data.tipo;
          document.getElementById('tipoHidden').value = data.tipo;

          if (data.es_automatico) {
              sub.innerText = "Vinculado a Inventario";
              infoText.innerText = "Nota: Este gasto es automático. Solo puedes editar descripción y notas.";
              
              // Bloquear campos críticos
              form.querySelector('[name="monto"]').readOnly = true;
              form.querySelector('[name="monto"]').classList.add('opacity-50');
              form.querySelector('[name="fecha"]').readOnly = true;
              form.querySelector('[name="fecha"]').classList.add('opacity-50');
              selectTipo.disabled = true;
          } else {
              sub.innerText = "Egreso de Caja";
              infoText.innerText = "Gasto manual. Puedes editar todos los campos.";
              // Asegurar que estén habilitados
              form.querySelector('[name="monto"]').readOnly = false;
              selectTipo.disabled = false;
          }

          document.getElementById('modalGastoTitulo').innerText = "Editar Gasto";
          document.getElementById('btnSubmitGasto').innerText = "Guardar Cambios";
          
          abrirModal('modalNuevoGasto');
      });
}