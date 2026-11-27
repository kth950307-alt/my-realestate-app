/**
 * 우리부동산 사장님 작업실 — 👥 손님 리마인드 백엔드 (Google Apps Script)
 * ------------------------------------------------------------------
 * 쓰는 순서
 *  1) https://script.google.com 에서 새 프로젝트를 만들고 이 파일 내용을 통째로 붙여넣습니다.
 *  2) 아래 PASSWORD 를 사장님만 아는 비밀번호로 바꿉니다. (손님 정보를 지키는 유일한 열쇠입니다)
 *  3) [배포] → [새 배포] → 유형 '웹 앱'
 *       · 실행 계정 : 나
 *       · 액세스 권한 : 모든 사용자
 *     → 배포 후 나오는 '웹 앱 URL'(.../exec)을 복사해 작업실 👥 손님 리마인드 화면에 붙여넣습니다.
 *  4) 코드를 고치면 [배포] → [배포 관리] → 연필 → 버전 '새 버전' 으로 다시 배포해야 반영됩니다.
 *
 * 동작
 *  · GET  ?pw=비번&action=customers   → 손님 목록(JSON)
 *  · GET  ?pw=비번&action=properties  → 공개 매물 요약 목록(JSON, 짝맞춤 추천용)
 *  · GET  ?pw=비번&action=update&row=12&status=...&remind=2026-12-01 ...
 *  · POST (본문 JSON 또는 폼) — 위와 같은 action 을 그대로 받습니다.
 *  · 브라우저 preflight(CORS)가 생기지 않도록 프론트에서는
 *    Content-Type: text/plain 으로 POST 하고, 막히면 같은 내용을 GET 으로 다시 보냅니다.
 */

/* ===== 설정 ===================================================== */
var PASSWORD = '563011';   // ★ 사장님만 아는 비밀번호로 꼭 바꿔 주세요.
var SPREADSHEET_ID = '1oTTZ1ok-quer9_NR5v5hEFYpRiOrR8tAwwo7UPnwRco';  // 내부 장부(비공개)
var PUBLIC_SHEET_ID = '1OofGenPy_CCWUz4GVNrmUPEOXkEcaCoQxEoAiMLQS5w'; // 공개 매물 시트
var CUSTOMERS_SHEET = 'customers';
var PUBLIC_SHEET = 'properties';
var TZ = 'Asia/Seoul';

/* customers 시트 열 순서 (A~Q) — app.py 의 CUST_COLUMNS 와 같습니다 */
var CUST_COLUMNS = [
  '등록일자', '중요도', '고객명', '연락처', '희망거래', '선호권역', '희망층수',
  '최소평수', '최대예산_보증금', '최대월세', '필수전력', '호이스트필수',
  '업종', '진행상태', '최근통화일', '리마인드예정일', '상세메모'
];

/* ===== 웹 요청 입구 ============================================= */
function doGet(e) {
  return handleRequest(e, (e && e.parameter) || {});
}

function doPost(e) {
  var body = {};
  try {
    body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
  } catch (err) {
    body = {};
  }
  var params = {};
  var k;
  for (k in ((e && e.parameter) || {})) params[k] = e.parameter[k];
  for (k in body) params[k] = body[k];
  return handleRequest(e, params);
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function handleRequest(e, p) {
  try {
    if (String(p.pw || '') !== PASSWORD) {
      return jsonOut({ ok: false, error: '비밀번호가 맞지 않습니다.' });
    }
    var action = String(p.action || 'customers');
    if (action === 'ping') return jsonOut({ ok: true, time: nowStamp() });
    if (action === 'customers') return jsonOut({ ok: true, customers: readCustomers() });
    if (action === 'properties') return jsonOut({ ok: true, properties: readProperties() });
    if (action === 'update') return jsonOut(updateCustomer(p));
    if (action === 'add') return jsonOut(addCustomer(p));
    return jsonOut({ ok: false, error: '알 수 없는 요청입니다: ' + action });
  } catch (err) {
    return jsonOut({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

/* ===== 손님 읽기 ================================================ */
function readCustomers() {
  var sh = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(CUSTOMERS_SHEET);
  if (!sh) throw new Error('"' + CUSTOMERS_SHEET + '" 시트를 찾지 못했습니다.');
  var last = sh.getLastRow();
  if (last < 2) return [];

  var width = CUST_COLUMNS.length;
  var values = sh.getRange(2, 1, last - 1, width).getDisplayValues();
  var out = [];
  for (var i = 0; i < values.length; i++) {
    var r = values[i];
    var name = String(r[2] || '').trim();
    var phone = String(r[3] || '').trim();
    if (!name && !phone) continue;              // 빈 줄은 건너뜀
    var o = { row: i + 2 };                     // 시트 실제 줄 번호
    for (var c = 0; c < width; c++) o[CUST_COLUMNS[c]] = String(r[c] || '').trim();
    out.push(o);
  }
  return out;
}

/* ===== 공개 매물 요약 (짝맞춤 추천용, 사진은 빼고 가볍게) ============ */
function readProperties() {
  var sh = SpreadsheetApp.openById(PUBLIC_SHEET_ID).getSheetByName(PUBLIC_SHEET);
  if (!sh) throw new Error('"' + PUBLIC_SHEET + '" 공개 시트를 찾지 못했습니다.');
  var last = sh.getLastRow();
  if (last < 2) return [];
  var values = sh.getRange(2, 1, last - 1, 26).getDisplayValues();
  var out = [];
  for (var i = 0; i < values.length; i++) {
    var r = values[i];
    if (!/^\d{4}-\d{2}-\d{2}/.test(String(r[0] || ''))) continue;   // 등록일자가 있는 줄만
    if (String(r[5] || '').indexOf('비공개') >= 0) continue;         // 비공개 매물 제외
    var id = String(r[1] || '').trim();
    if (!id) continue;
    out.push({
      id: id,
      deal: String(r[2] || '').trim(),
      region: String(r[3] || '').trim(),
      floor: String(r[4] || '').trim(),
      title: String(r[6] || '').trim(),
      price: String(r[7] || '').trim(),
      dep: toNum(r[8]),
      rent: toNum(r[9]),
      area: toNum(r[10]),
      office: toNum(r[11]),
      height: String(r[12] || '').trim(),
      power: toNum(r[13]),
      hoist: String(r[14] || '').trim(),
      hoistSpec: String(r[15] || '').trim(),
      road: String(r[16] || '').trim(),
      zone: String(r[22] || '').trim(),
      feature: String(r[24] || '').trim()
    });
  }
  return out;
}

/* ===== 손님 정보 업데이트 ======================================== */
function updateCustomer(p) {
  var row = Number(p.row);
  if (!row || row < 2) throw new Error('어느 줄(row)을 바꿀지 알 수 없습니다.');

  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var sh = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(CUSTOMERS_SHEET);
    if (!sh) throw new Error('"' + CUSTOMERS_SHEET + '" 시트를 찾지 못했습니다.');
    if (row > sh.getLastRow()) throw new Error('해당 손님 줄을 찾지 못했습니다. 새로고침 후 다시 시도해 주세요.');

    var idx = {};
    for (var i = 0; i < CUST_COLUMNS.length; i++) idx[CUST_COLUMNS[i]] = i + 1;

    var sets = [];
    if (p.status != null && p.status !== '') sets.push(['진행상태', String(p.status)]);
    if (p.remind != null) sets.push(['리마인드예정일', String(p.remind)]);
    if (p.recent != null) sets.push(['최근통화일', String(p.recent)]);
    if (p.memo != null) sets.push(['상세메모', String(p.memo)]);
    if (p.priority != null) sets.push(['중요도', String(p.priority)]);
    if (!sets.length) throw new Error('바꿀 내용이 없습니다.');

    for (var s = 0; s < sets.length; s++) {
      sh.getRange(row, idx[sets[s][0]]).setValue(sets[s][1]);
    }
    SpreadsheetApp.flush();

    var changed = [];
    for (var c = 0; c < sets.length; c++) changed.push(sets[c][0]);
    return { ok: true, row: row, changed: changed };
  } finally {
    lock.releaseLock();
  }
}

/* ===== 신규 손님 등록 =========================================== */
function addCustomer(p) {
  var name = String(p.name || '').trim();
  var phone = String(p.phone || '').trim();
  if (!name) throw new Error('손님 이름을 넣어 주세요.');
  if (!phone) throw new Error('연락처를 넣어 주세요.');

  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var sh = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(CUSTOMERS_SHEET);
    if (!sh) throw new Error('"' + CUSTOMERS_SHEET + '" 시트를 찾지 못했습니다.');

    var today = todayString();
    var remind = String(p.remind || '').trim() || addDays(today, 3);
    var row = [
      today,                                   // 등록일자
      String(p.priority || '보통').trim(),      // 중요도
      name,                                    // 고객명
      phone,                                   // 연락처
      String(p.deal || '').trim(),              // 희망거래
      String(p.region || '').trim(),            // 선호권역
      String(p.floor || '').trim(),             // 희망층수
      String(p.minArea || '').trim(),           // 최소평수
      String(p.deposit || '').trim(),           // 최대예산_보증금
      String(p.rent || '').trim(),              // 최대월세
      String(p.power || '').trim(),             // 필수전력
      String(p.hoist || '').trim(),             // 호이스트필수
      String(p.industry || '').trim(),          // 업종
      String(p.status || '📞 콜백대기(리마인드)').trim(),  // 진행상태
      today,                                   // 최근통화일
      remind,                                  // 리마인드예정일
      String(p.memo || '').trim()               // 상세메모
    ];
    sh.appendRow(row);
    SpreadsheetApp.flush();
    return { ok: true, row: sh.getLastRow(), remind: remind };
  } finally {
    lock.releaseLock();
  }
}

/* ===== 도우미 ================================================== */
function toNum(v) {
  var m = String(v == null ? '' : v).replace(/,/g, '').match(/[\d.]+/);
  return m ? parseFloat(m[0]) : 0;
}

function todayString() {
  return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
}

function nowStamp() {
  return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd HH:mm:ss');
}

function addDays(yyyymmdd, days) {
  var m = String(yyyymmdd || '').match(/(\d{4})-(\d{2})-(\d{2})/);
  var base = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date();
  base.setDate(base.getDate() + Number(days || 0));
  return Utilities.formatDate(base, TZ, 'yyyy-MM-dd');
}

/* ===== 설치 자가 점검용 (편집기에서 직접 실행) ===================== */
function testRead() {
  var list = readCustomers();
  Logger.log('손님 %s명 / 첫 손님: %s', list.length, list.length ? list[0]['고객명'] : '-');
}
