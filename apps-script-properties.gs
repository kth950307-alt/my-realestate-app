/**
 * 우리부동산 사장님 작업실 — 🏭 매물 10초 등록·수정 백엔드 (Google Apps Script)
 * ------------------------------------------------------------------
 * 쓰는 순서 (3단계 · 1회만)
 *  1) https://script.google.com → 새 프로젝트 → 이 파일 내용을 통째로 붙여넣습니다.
 *  2) 아래 PASSWORD 를 사장님만 아는 비밀번호로 맞춥니다. (내부 장부를 지키는 유일한 열쇠)
 *  3) [배포] → [새 배포] → 유형 '웹 앱'
 *       · 실행 계정 : 나
 *       · 액세스 권한 : 모든 사용자
 *     → 배포 후 나오는 '웹 앱 URL'(.../exec)을 작업실 🏭 매물 10초 등록 화면의 [연결 설정]에 붙여넣습니다.
 *  ※ 코드를 고치면 [배포] → [배포 관리] → 연필 → 버전 '새 버전' 으로 다시 배포해야 반영됩니다.
 *
 * 동작
 *  · GET  ?pw=비번&action=ping                → 연결 확인
 *  · GET  ?pw=비번&action=list                → 매물 전체 목록(JSON, 대표사진은 빼고 가볍게)
 *  · POST ?action=add&...                     → properties 탭에 새 줄 추가 (매물번호 자동 W-YYMMDD-HHMM)
 *  · POST ?action=update&row=123&...          → 기존 줄의 지정한 칸만 수정
 *
 * 안전장치
 *  · 상세지번·건물주성함·건물주연락처 3칸은 내부 장부에만 저장하고
 *    공개 시트(손님용 홈페이지)에는 절대 쓰지 않습니다. (항상 공백)
 *  · 비공개 매물은 공개 시트에 넣지 않고, 공개→비공개로 바꾸면 공개 시트에서 그 줄을 지웁니다.
 *  · 브라우저 preflight(CORS)가 생기지 않도록 프론트에서는 Content-Type: text/plain 으로 POST 하고,
 *    막히면 같은 내용을 GET 으로 다시 보냅니다.
 */

/* ===== 설정 ===================================================== */
var PASSWORD = '563011';   // ★ 사장님만 아는 비밀번호 (손님 리마인드와 같은 번호를 쓰면 편합니다)
var SPREADSHEET_ID = '1oTTZ1ok-quer9_NR5v5hEFYpRiOrR8tAwwo7UPnwRco';  // 내부 장부(비공개)
var PUBLIC_SHEET_ID = '1OofGenPy_CCWUz4GVNrmUPEOXkEcaCoQxEoAiMLQS5w'; // 공개 매물 시트(손님 홈페이지)
var SHEET_NAME = 'properties';
var TZ = 'Asia/Seoul';

/* properties 시트 열 순서 (A~Z, 26칸) — 우리부동산 앱(app.py)의 PROP_COLUMNS 와 같습니다 */
var COLS = [
  '등록일자', '매물번호', '거래구분', '권역', '해당층수', '홈페이지노출',
  '매물제목', '가격설명', '보증금_매매가', '월세', '전용평수', '사무실평수',
  '층고', '전력', '호이스트유무', '호이스트제원', '도로조건', '입주날짜',
  '추천업종', '상세지번', '건물주성함', '건물주연락처', '용도지역',
  '사용승인일', '핵심특징', '대표사진'
];

/* 절대 공개 시트에 나가면 안 되는 칸 */
var SENSITIVE = ['상세지번', '건물주성함', '건물주연락처'];

/* 프론트에서 넘어온 짧은 이름 → 시트 열 이름 */
var FIELD_MAP = {
  deal: '거래구분', region: '권역', floor: '해당층수', expose: '홈페이지노출',
  title: '매물제목', priceDesc: '가격설명', dep: '보증금_매매가', rent: '월세',
  area: '전용평수', office: '사무실평수', height: '층고', power: '전력',
  hoist: '호이스트유무', hoistSpec: '호이스트제원', road: '도로조건',
  moveIn: '입주날짜', industry: '추천업종', zone: '용도지역', approve: '사용승인일',
  jibun: '상세지번', owner: '건물주성함', ownerPhone: '건물주연락처', feature: '핵심특징'
};

/* ===== 웹 요청 입구 ============================================= */
function doGet(e) {
  return handleRequest((e && e.parameter) || {});
}

function doPost(e) {
  var body = {};
  try { body = JSON.parse((e && e.postData && e.postData.contents) || '{}'); } catch (err) { body = {}; }
  var params = {}, k;
  for (k in ((e && e.parameter) || {})) params[k] = e.parameter[k];
  for (k in body) params[k] = body[k];
  return handleRequest(params);
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function handleRequest(p) {
  try {
    if (String(p.pw || '') !== PASSWORD) return jsonOut({ ok: false, error: '비밀번호가 맞지 않습니다.' });
    var action = String(p.action || 'ping');
    if (action === 'ping') return jsonOut(pingInfo());
    if (action === 'list') return jsonOut({ ok: true, properties: listProperties() });
    if (action === 'add') return jsonOut(addProperty(p));
    if (action === 'update') return jsonOut(updateProperty(p));
    return jsonOut({ ok: false, error: '알 수 없는 요청입니다: ' + action });
  } catch (err) {
    return jsonOut({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

/* ===== 시트 열기 + 머리글 확인 =================================== */
function openProp() {
  var sh = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  if (!sh) throw new Error('"' + SHEET_NAME + '" 시트를 찾지 못했습니다.');
  return sh;
}

function checkHeader(sh) {
  var head = sh.getRange(1, 1, 1, COLS.length).getDisplayValues()[0];
  for (var i = 0; i < COLS.length; i++) {
    if (String(head[i] || '').trim() !== COLS[i]) {
      throw new Error('열 순서가 예상과 다릅니다. ' + (i + 1) + '번째 칸이 "' + COLS[i] + '"이어야 하는데 "' +
        String(head[i] || '') + '"입니다. 시트 머리글을 확인해 주세요.');
    }
  }
}

function pingInfo() {
  var sh = openProp();
  checkHeader(sh);
  return {
    ok: true,
    sheetTitle: '우리부동산 장부 · properties',
    rows: Math.max(0, sh.getLastRow() - 1),
    time: nowStamp()
  };
}

/* ===== 목록 읽기 (대표사진 제외) ================================= */
function listProperties() {
  var sh = openProp();
  checkHeader(sh);
  var last = sh.getLastRow();
  if (last < 2) return [];
  /* 대표사진(Z열, base64 수만 자)은 빼고 A~Y만 읽어 가볍게 */
  var width = COLS.length - 1;
  var values = sh.getRange(2, 1, last - 1, width).getDisplayValues();
  var out = [];
  for (var i = 0; i < values.length; i++) {
    var r = values[i];
    var no = String(r[1] || '').trim();
    var date = String(r[0] || '').trim();
    if (!no && !date) continue;
    var o = { row: i + 2 };
    for (var c = 0; c < width; c++) {
      o[COLS[c]] = String(r[c] == null ? '' : r[c]).trim();
    }
    out.push(o);
  }
  return out;
}

/* ===== 새 매물 추가 ============================================= */
function addProperty(p) {
  var deal = str(p.deal);
  var region = str(p.region);
  if (!deal) throw new Error('거래구분을 넣어 주세요.');
  if (!region) throw new Error('권역을 넣어 주세요.');

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = openProp();
    checkHeader(sh);

    var no = nextPropertyNo(sh);
    var expose = normalizeExpose(p.expose);
    var row = [];
    for (var i = 0; i < COLS.length; i++) row.push('');

    set(row, '등록일자', todayString());
    set(row, '매물번호', no);
    set(row, '거래구분', deal);
    set(row, '권역', region);
    set(row, '해당층수', str(p.floor));
    set(row, '홈페이지노출', expose);
    set(row, '매물제목', str(p.title) || (region + ' ' + str(p.floor) + ' ' + str(p.area) + '평 ' + deal).replace(/\s+/g, ' ').trim());
    set(row, '가격설명', str(p.priceDesc));
    set(row, '보증금_매매가', numStr(p.dep));
    set(row, '월세', numStr(p.rent));
    set(row, '전용평수', numStr(p.area));
    set(row, '사무실평수', numStr(p.office));
    set(row, '층고', str(p.height));
    set(row, '전력', str(p.power));
    set(row, '호이스트유무', str(p.hoist) === '있음' ? '있음' : '없음');
    set(row, '호이스트제원', str(p.hoist) === '있음' ? (str(p.hoistSpec) || '있음') : '없음');
    set(row, '도로조건', str(p.road));
    set(row, '입주날짜', str(p.moveIn));
    set(row, '추천업종', str(p.industry));
    set(row, '상세지번', str(p.jibun));
    set(row, '건물주성함', str(p.owner));
    set(row, '건물주연락처', str(p.ownerPhone));
    set(row, '용도지역', str(p.zone));
    set(row, '사용승인일', str(p.approve));
    set(row, '핵심특징', str(p.feature));
    set(row, '대표사진', '');

    sh.appendRow(row);
    SpreadsheetApp.flush();
    var newRow = sh.getLastRow();

    var publicAdded = false;
    if (isPublicExpose(expose)) {
      try { publicAdded = appendPublic(row); } catch (err) { publicAdded = false; }
    }

    return { ok: true, no: no, row: newRow, expose: expose, publicAdded: publicAdded };
  } finally {
    lock.releaseLock();
  }
}

/* ===== 기존 매물 수정 (넘어온 칸만) =============================== */
function updateProperty(p) {
  var rowNo = Number(p.row);
  if (!rowNo || rowNo < 2) throw new Error('어느 줄(row)을 바꿀지 알 수 없습니다.');

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = openProp();
    checkHeader(sh);
    if (rowNo > sh.getLastRow()) throw new Error('해당 매물 줄을 찾지 못했습니다. 새로고침 후 다시 시도해 주세요.');

    var current = sh.getRange(rowNo, 1, 1, COLS.length).getDisplayValues()[0];
    var changed = [];
    var next = current.slice();

    for (var key in FIELD_MAP) {
      if (p[key] === undefined || p[key] === null) continue;
      var col = FIELD_MAP[key];
      var val = (col === '홈페이지노출') ? normalizeExpose(p[key]) : str(p[key]);
      var idx = COLS.indexOf(col);
      if (idx < 0) continue;
      if (String(current[idx] || '').trim() === String(val).trim()) continue;
      next[idx] = val;
      changed.push(col);
    }

    if (!changed.length) return { ok: true, row: rowNo, changed: [], note: '바뀐 내용이 없습니다.' };

    for (var c = 0; c < changed.length; c++) {
      var i = COLS.indexOf(changed[c]);
      sh.getRange(rowNo, i + 1).setValue(next[i]);
    }
    SpreadsheetApp.flush();

    /* 공개 시트 동기화 */
    var no = String(next[1] || '').trim();
    var wantPublic = isPublicExpose(String(next[5] || ''));
    var result = { publicAdded: false, publicRemoved: false, publicUpdated: false };
    if (no) {
      try {
        result = syncPublic(no, next, changed, wantPublic);
      } catch (err) {
        result.error = String(err && err.message ? err.message : err);
      }
    }

    return {
      ok: true, row: rowNo, no: no, changed: changed,
      publicAdded: result.publicAdded, publicRemoved: result.publicRemoved, publicUpdated: result.publicUpdated,
      publicError: result.error || ''
    };
  } finally {
    lock.releaseLock();
  }
}

/* ===== 공개 시트(손님 홈페이지) 동기화 ============================ */
function openPublic() {
  var sh = SpreadsheetApp.openById(PUBLIC_SHEET_ID).getSheetByName(SHEET_NAME);
  if (!sh) throw new Error('공개 시트 "' + SHEET_NAME + '"를 찾지 못했습니다.');
  return sh;
}

function publicRowIndex(sh, no) {
  var last = sh.getLastRow();
  if (last < 2) return -1;
  var ids = sh.getRange(2, 2, last - 1, 1).getDisplayValues();
  for (var i = 0; i < ids.length; i++) {
    if (String(ids[i][0] || '').trim() === no) return i + 2;
  }
  return -1;
}

function sanitizeForPublic(row) {
  var out = row.slice();
  for (var i = 0; i < SENSITIVE.length; i++) {
    var idx = COLS.indexOf(SENSITIVE[i]);
    if (idx >= 0) out[idx] = '';
  }
  return out;
}

function appendPublic(row) {
  var sh = openPublic();
  sh.appendRow(sanitizeForPublic(row));
  SpreadsheetApp.flush();
  return true;
}

function syncPublic(no, row, changed, wantPublic) {
  var sh = openPublic();
  var at = publicRowIndex(sh, no);
  var res = { publicAdded: false, publicRemoved: false, publicUpdated: false };

  if (wantPublic) {
    if (at < 0) {
      sh.appendRow(sanitizeForPublic(row));
      SpreadsheetApp.flush();
      res.publicAdded = true;
    } else {
      for (var c = 0; c < changed.length; c++) {
        var i = COLS.indexOf(changed[c]);
        if (i < 0) continue;
        var v = SENSITIVE.indexOf(changed[c]) >= 0 ? '' : row[i];
        sh.getRange(at, i + 1).setValue(v);
      }
      /* 민감 3칸은 무슨 일이 있어도 비웁니다 */
      for (var s = 0; s < SENSITIVE.length; s++) {
        var si = COLS.indexOf(SENSITIVE[s]);
        if (si >= 0) sh.getRange(at, si + 1).setValue('');
      }
      SpreadsheetApp.flush();
      res.publicUpdated = true;
    }
  } else if (at >= 0) {
    sh.deleteRow(at);
    SpreadsheetApp.flush();
    res.publicRemoved = true;
  }
  return res;
}

/* ===== 도우미 ================================================== */
function str(v) { return String(v == null ? '' : v).trim(); }

function numStr(v) {
  var s = String(v == null ? '' : v).replace(/[,\s]/g, '');
  if (!s) return '';
  var m = s.match(/-?\d+(\.\d+)?/);
  return m ? m[0] : s;
}

function set(row, colName, value) {
  var i = COLS.indexOf(colName);
  if (i >= 0) row[i] = value;
}

function isPublicExpose(v) {
  v = String(v || '');
  return v.indexOf('공개') >= 0 && v.indexOf('비공개') < 0;
}

function normalizeExpose(v) {
  return isPublicExpose(v) ? '노출(공개)' : '비공개(내부장부용)';
}

function todayString() {
  return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
}

function nowStamp() {
  return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd HH:mm:ss');
}

/* W-YYMMDD-HHMM — 같은 분에 이미 번호가 있으면 1분씩 뒤로 밀어 겹치지 않게 */
function nextPropertyNo(sh) {
  var last = sh.getLastRow();
  var used = {};
  if (last >= 2) {
    var ids = sh.getRange(2, 2, last - 1, 1).getDisplayValues();
    for (var i = 0; i < ids.length; i++) used[String(ids[i][0] || '').trim()] = true;
  }
  var now = new Date();
  for (var step = 0; step < 300; step++) {
    var t = new Date(now.getTime() + step * 60000);
    var no = 'W-' + Utilities.formatDate(t, TZ, 'yyMMdd-HHmm');
    if (!used[no]) return no;
  }
  return 'W-' + Utilities.formatDate(now, TZ, 'yyMMdd-HHmmss');
}

/* ===== 설치 자가 점검용 (편집기에서 직접 실행) ===================== */
function testPing() {
  var info = pingInfo();
  Logger.log('연결 OK · 매물 %s건 · %s', info.rows, info.time);
}

function testRead() {
  var list = listProperties();
  Logger.log('매물 %s건 / 최근: %s', list.length, list.length ? (list[list.length - 1]['매물번호'] + ' ' + list[list.length - 1]['매물제목']) : '-');
}
