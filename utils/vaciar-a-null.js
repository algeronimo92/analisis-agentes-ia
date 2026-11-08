// Nodo Code 'Vaciar a null' del workflow del analista (rpSHUZd1Et3vkK4n).
// Va entre 'agente analista1' y 'update lead'. Pegar TAL CUAL en n8n.
//
// POR QUE EXISTE: el schema de function calling de Gemini no acepta union types
// (ningun campo del parser puede ser nullable, ver la nota del 30-jul-2026 en
// prompts/agente-analista-leads.md), asi que el agente devuelve el centinela
// "no_especificado" donde antes devolvia null. Aqui se rehidrata a null y se
// aplican las reglas de coherencia antes de escribir en la BD.
//
// Mantiene el wrapper "output": 'update lead' y 'actualizar estado lead'
// siguen leyendo $json.output.* sin cambios.

const ESTADOS = ['nuevo','en_diagnostico','calificado','oferta_presentada','en_objecion','agendado','cliente_activo','postventa','en_seguimiento','en_nutricion','perdido','descalificado','baja'];

// Valores validos en la BD. El schema tambien permite 'no_especificado' (por la
// prohibicion de nullables), y ese cae a null como cualquier otro centinela.
const TIPOS_OBJECION = ['indecision','concreto'];

// El centinela del prompt ("no_especificado") mas las variantes que el modelo
// podria improvisar. Se compara normalizado, asi que basta la forma en minusculas
// y con espacios: "No_Especificado." tambien entra.
const SIN_DATO = new Set(['no especificado','no aplica','no disponible','no hay','desconocido',
  'ninguna','ninguno','ningun','null','nulo','none','undefined','n/a','na','nada',
  'sin dato','sin datos','sin especificar','-','--','']);

// minusculas, sin tildes, sin guiones bajos y sin puntuacion de borde:
// "No_Especificado." -> "no especificado"
function clave(v) {
  return String(v)
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[_\s]+/g, ' ')
    .replace(/^[\s"'¿¡(]+/, '')
    .replace(/[\s"'.,;:!?)]+$/, '')
    .trim();
}

// Devuelve el valor tal cual lo escribio el modelo (con sus tildes), o null si
// es un centinela de "sin dato".
function aNull(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return SIN_DATO.has(clave(s)) ? null : s;
}

function aBool(v) {
  if (typeof v === 'boolean') return v;
  const s = clave(v);
  return s === 'true' || s === 'si' || s === '1';
}

// fecha_recontacto -> YYYY-MM-DD, y solo si la fecha existe de verdad
// (2026-02-31 la rechazaria Postgres y tumbaria el workflow).
function fechaONull(v) {
  const s = aNull(v);
  if (!s) return null;
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return null;
  const d = new Date(m[0] + 'T00:00:00Z');
  if (isNaN(d.getTime()) || d.getUTCDate() !== Number(m[3]) || d.getUTCMonth() + 1 !== Number(m[2])) return null;
  return m[0];
}

// proxima_cita -> se conserva tal cual (ISO 8601 con zona de Peru) si es parseable.
function timestampONull(v) {
  const s = aNull(v);
  if (!s) return null;
  if (!/\d{4}-\d{2}-\d{2}/.test(s)) return null;
  return isNaN(new Date(s.replace(' ', 'T')).getTime()) ? null : s;
}

// El agente entrega el objeto en .output. Si el parser viniera desactivado, el
// texto llega como string (a veces envuelto en ```json): lo rescatamos.
function salidaDelAgente(json) {
  let d = (json && json.output !== undefined) ? json.output : json;
  if (typeof d === 'string') {
    let t = d.trim();
    if (t.startsWith('```')) t = t.replace(/^```[a-z]*\s*/i, '').replace(/```\s*$/, '').trim();
    try { d = JSON.parse(t); } catch (e) {
      throw new Error('El agente no devolvio JSON parseable: ' + t.slice(0, 200));
    }
  }
  if (!d || typeof d !== 'object') throw new Error('El agente no devolvio un objeto: ' + JSON.stringify(d));
  return d;
}

const salida = [];

for (const item of $input.all()) {
  const d = salidaDelAgente(item.json);

  // estado: unico campo sin fallback. Si no es valido, se corta la ejecucion sin
  // escribir nada (guardarrail 4: jamas un estado por defecto).
  const estado = clave(d.estado).replace(/ /g, '_');   // "En Diagnóstico" -> en_diagnostico
  if (!ESTADOS.includes(estado)) {
    throw new Error('Estado invalido devuelto por el modelo: ' + JSON.stringify(d.estado)
      + ' · salida completa: ' + JSON.stringify(d).slice(0, 400));
  }

  // tipo_objecion solo tiene sentido en en_objecion
  let tipo_objecion = aNull(d.tipo_objecion);
  if (tipo_objecion) tipo_objecion = clave(tipo_objecion).replace(/ /g, '_');
  if (!TIPOS_OBJECION.includes(tipo_objecion)) tipo_objecion = null;
  if (estado !== 'en_objecion') tipo_objecion = null;

  // razon_perdido solo en perdido / descalificado
  let razon_perdido = aNull(d.razon_perdido);
  if (estado !== 'perdido' && estado !== 'descalificado') razon_perdido = null;

  // proxima_cita solo en agendado
  let proxima_cita = timestampONull(d.proxima_cita);
  if (estado !== 'agendado') proxima_cita = null;

  // telefono: solo digitos, y descartamos basura corta
  let telefono = aNull(d.telefono);
  if (telefono) {
    telefono = telefono.replace(/\D/g, '');
    if (telefono.length < 6) telefono = null;
  }

  salida.push({
    json: {
      output: {
        razonamiento: aNull(d.razonamiento),
        nombre: aNull(d.nombre),
        telefono: telefono,
        estado: estado,
        tipo_objecion: tipo_objecion,
        servicio_interes: aNull(d.servicio_interes),
        razon_perdido: razon_perdido,
        fecha_recontacto: fechaONull(d.fecha_recontacto),
        proxima_cita: proxima_cita,
        con_especialista: aBool(d.con_especialista),
        notas: aNull(d.notas)
      }
    }
  });
}

return salida;
