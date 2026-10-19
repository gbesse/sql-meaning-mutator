const text = {
  fr: {
    eyebrow: 'SQL-LLM · DES PREUVES PLUTÔT QUE DES APPARENCES',
    title: 'La requête passe.\nLe résultat est faux.',
    lede: 'Une base trop simple peut valider une mauvaise requête. Faites évoluer les données, conservez les contraintes relationnelles et obtenez un petit contre-exemple rejouable.',
    intent: 'L’intention métier',
    seed: 'LE JEU INITIAL PASSE',
    trap: 'Une ligne par commande masque la multiplication des montants. Le moteur cherche un jeu qui distingue les deux requêtes.',
    search: 'Chercher le contre-exemple →',
    fix: 'Essayer la requête de référence',
    reset: 'Rétablir la requête piégée',
    reference: 'Référence fournie',
    candidate: 'Requête candidate',
    cases: 'jeux examinés',
    rows: 'lignes du témoin',
    minimal: 'minimalité locale',
    difference: 'Même base, résultats différents',
    witness: 'Le témoin relationnel',
    download: 'Exporter le cas rejouable',
    limits:
      'Recherche bornée dans SQLite, sans modèle ni accès à une base réelle. La référence est fournie par l’utilisateur : elle peut aussi être fausse. Aucun contre-exemple trouvé ne prouve la correction métier. La minimalité concerne les suppressions de lignes et leurs dépendances, en conservant le type d’écart.',
    busy: 'Recherche et réduction du témoin…',
    found: 'CONTRE-EXEMPLE TROUVÉ',
    notFound: 'AUCUN TÉMOIN TROUVÉ',
    queryError: 'REQUÊTE OU DONNÉES INVALIDES',
    yes: 'vérifiée',
    partial: 'non prouvée',
    ready: 'Prêt à tester les hypothèses du jeu initial.',
    error: 'Entrée non valide ou serveur indisponible.',
    none: 'Aucun témoin : ce résultat ne prouve pas la correction métier.',
    path: 'Mutation',
    clone_row: 'dupliquer une ligne',
    delete_row: 'supprimer une ligne',
    set_cell: 'modifier une cellule',
    synthetic: 'Données synthétiques',
  },
  en: {
    eyebrow: 'SQL-LLM · EVIDENCE OVER APPEARANCES',
    title: 'The query passes.\nThe answer is wrong.',
    lede: 'An overly simple database can validate the wrong query. Mutate data, preserve relational constraints, and obtain a small replayable counterexample.',
    intent: 'Business intent',
    seed: 'THE INITIAL FIXTURE PASSES',
    trap: 'One line per order hides multiplied amounts. The engine searches for data that distinguish the two queries.',
    search: 'Find the counterexample →',
    fix: 'Try the reference query',
    reset: 'Restore the flawed query',
    reference: 'Supplied reference',
    candidate: 'Candidate query',
    cases: 'fixtures checked',
    rows: 'witness rows',
    minimal: 'local minimality',
    difference: 'Same database, different answers',
    witness: 'The relational witness',
    download: 'Export replayable case',
    limits:
      'Bounded SQLite search, with no model or live database access. The reference is user supplied and may also be wrong. Finding no counterexample does not prove business correctness. Minimality covers row deletions and their dependencies while preserving the mismatch category.',
    busy: 'Searching and reducing the witness…',
    found: 'COUNTEREXAMPLE FOUND',
    notFound: 'NO WITNESS FOUND',
    queryError: 'INVALID QUERY OR FIXTURE',
    yes: 'checked',
    partial: 'unproven',
    ready: 'Ready to test the initial fixture’s assumptions.',
    error: 'Invalid input or server unavailable.',
    none: 'No witness: this does not prove business correctness.',
    path: 'Mutation',
    clone_row: 'duplicate a row',
    delete_row: 'delete a row',
    set_cell: 'change a cell',
    synthetic: 'Synthetic data',
  },
  es: {
    eyebrow: 'SQL-LLM · PRUEBAS FRENTE A APARIENCIAS',
    title: 'La consulta pasa.\nLa respuesta es incorrecta.',
    lede: 'Una base demasiado simple puede validar una consulta incorrecta. Modifica los datos, conserva las restricciones relacionales y obtiene un pequeño contraejemplo reproducible.',
    intent: 'Intención de negocio',
    seed: 'EL CASO INICIAL PASA',
    trap: 'Una línea por pedido oculta la multiplicación de importes. El motor busca datos que distingan las dos consultas.',
    search: 'Buscar el contraejemplo →',
    fix: 'Probar la consulta de referencia',
    reset: 'Restaurar la consulta errónea',
    reference: 'Referencia proporcionada',
    candidate: 'Consulta candidata',
    cases: 'casos examinados',
    rows: 'filas del testigo',
    minimal: 'minimalidad local',
    difference: 'Misma base, respuestas distintas',
    witness: 'El testigo relacional',
    download: 'Exportar caso reproducible',
    limits:
      'Búsqueda acotada en SQLite, sin modelo ni acceso a bases reales. La referencia la proporciona el usuario y también puede ser errónea. No encontrar contraejemplos no demuestra corrección de negocio. La minimalidad abarca eliminaciones de filas y dependencias, conservando el tipo de diferencia.',
    busy: 'Buscando y reduciendo el testigo…',
    found: 'CONTRAEJEMPLO ENCONTRADO',
    notFound: 'SIN TESTIGO ENCONTRADO',
    queryError: 'CONSULTA O DATOS NO VÁLIDOS',
    yes: 'verificada',
    partial: 'no demostrada',
    ready: 'Listo para comprobar las hipótesis del caso inicial.',
    error: 'Entrada no válida o servidor no disponible.',
    none: 'Sin testigo: no demuestra corrección de negocio.',
    path: 'Mutación',
    clone_row: 'duplicar una fila',
    delete_row: 'eliminar una fila',
    set_cell: 'cambiar una celda',
    synthetic: 'Datos sintéticos',
  },
};
const lang = new URLSearchParams(location.search).get('lang') || 'en',
  m = text[lang] || text.en;
document.documentElement.lang = text[lang] ? lang : 'en';
document.querySelectorAll('[data-i18n]').forEach((x) => (x.textContent = m[x.dataset.i18n]));
document.querySelectorAll('nav a').forEach((a) => {
  if (a.textContent.toLowerCase() === document.documentElement.lang)
    a.setAttribute('aria-current', 'page');
});
const $ = (id) => document.getElementById(id),
  el = (tag, value, cls) => {
    const x = document.createElement(tag);
    if (value !== undefined) x.textContent = value;
    if (cls) x.className = cls;
    return x;
  };
let initial, report;
function render(r) {
  report = r;
  $('cases').textContent = r.cases_checked ?? '—';
  $('rows').textContent = r.row_count ?? '—';
  $('minimal').textContent = r.row_deletion_minimal ? m.yes : m.partial;
  $('verdict').textContent =
    r.status === 'counterexample'
      ? m.found
      : r.status === 'query_or_fixture_error'
        ? m.queryError
        : m.notFound;
  $('digest').textContent = r.input_sha256;
  $('tables').replaceChildren();
  $('expected').textContent = r.comparison ? JSON.stringify(r.comparison.reference, null, 2) : '—';
  $('actual').textContent = r.comparison ? JSON.stringify(r.comparison.candidate, null, 2) : '—';
  $('status').textContent =
    r.status === 'counterexample'
      ? m.found
      : r.status === 'query_or_fixture_error'
        ? m.queryError
        : m.none;
  if (r.witness) {
    for (const change of r.mutation_path) {
      $('tables').append(el('p', `${m.path}: ${m[change.operation]} · ${change.table}`, 'hint'));
    }
    for (const [name, data] of Object.entries(r.witness.tables)) {
      const box = el('div', undefined, 'witness-table');
      box.append(el('h3', `${name} · ${data.rows.length}`));
      const table = el('table'),
        head = el('tr');
      for (const c of Object.keys(data.columns)) head.append(el('th', c));
      table.append(head);
      for (const row of data.rows) {
        const tr = el('tr');
        for (const c of Object.keys(data.columns))
          tr.append(el('td', row[c] === null ? 'NULL' : String(row[c])));
        table.append(tr);
      }
      box.append(table);
      $('tables').append(box);
    }
  } else
    $('tables').append(
      el('p', r.status === 'query_or_fixture_error' ? m.queryError : m.none, 'hint'),
    );
}
async function run() {
  $('search').disabled = true;
  $('status').textContent = m.busy;
  try {
    const caseData = structuredClone(initial);
    caseData.candidate_sql = $('query').value;
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(caseData),
    });
    if (!res.ok) throw Error();
    render(await res.json());
  } catch {
    $('status').textContent = m.error;
  } finally {
    $('search').disabled = false;
  }
}
$('search').addEventListener('click', run);
$('fix').addEventListener('click', () => {
  $('query').value = initial.reference_sql;
  run();
});
$('reset').addEventListener('click', () => {
  $('query').value = initial.candidate_sql;
  run();
});
$('download').addEventListener('click', () => {
  if (!report?.witness) return;
  const url = URL.createObjectURL(
      new Blob([JSON.stringify(report.witness, null, 2)], { type: 'application/json' }),
    ),
    a = el('a');
  a.href = url;
  a.download = 'sql-counterexample.json';
  a.click();
  URL.revokeObjectURL(url);
});
try {
  const response = await fetch('/api/example');
  if (!response.ok) throw Error();
  const data = await response.json();
  initial = data.case;
  $('intent').textContent = initial.intent[document.documentElement.lang];
  $('query').value = initial.candidate_sql;
  $('reference').textContent = initial.reference_sql;
  $('status').textContent = m.ready;
} catch {
  $('status').textContent = m.error;
}
