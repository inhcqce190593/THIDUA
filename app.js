import express from "express";
import session from "express-session";
import flash from "connect-flash";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";
import mysql from "mysql2/promise";
import ExcelJS from "exceljs";

dotenv.config();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

// --- Config ---
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use("/static", express.static(path.join(__dirname, "static")));
app.set("views", path.join(__dirname, "templates"));
app.engine("html", (await import("ejs")).renderFile);
app.set("view engine", "html");

app.use(
  session({
    secret: process.env.SESSION_SECRET || "secret123",
    resave: false,
    saveUninitialized: false
  })
);
app.use(flash());

// Flash → locals
app.use((req, res, next) => {
  res.locals.flash_success = req.flash("success");
  res.locals.flash_error = req.flash("error");
  res.locals.flash_info = req.flash("info");
  res.locals.flash_warning = req.flash("warning");
  res.locals.session = req.session;
  next();
});

// --- DB pool ---
const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASS || "",
  database: process.env.DB_NAME,
  charset: process.env.DB_CHARSET || "utf8mb4",
  waitForConnections: true,
  connectionLimit: 10
});

// --- Helpers ---
function loginRequired(req, res, next) {
  if (!req.session.username) return res.redirect("/login");
  next();
}

// Group & rank giống Python
function rankByWeekAndKhoi(rows) {
  const grouped = {};
  for (const r of rows) {
    const key = `${r.tuan}||${r.khoi ?? "Unknown"}`;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(r);
  }
  const out = [];
  const keys = Object.keys(grouped).sort();
  for (const key of keys) {
    const list = grouped[key].sort((a, b) => (b.tong_diem_chung ?? 0) - (a.tong_diem_chung ?? 0));
    let currentRank = 1;
    let sameCount = 1;
    let prev = null;
    list.forEach((item, i) => {
      if (i === 0) {
        item.xep_hang = currentRank;
      } else {
        if ((item.tong_diem_chung ?? 0) < (prev ?? 0)) {
          currentRank += sameCount;
          sameCount = 1;
        } else {
          sameCount += 1;
        }
        item.xep_hang = currentRank;
      }
      prev = item.tong_diem_chung ?? 0;
      out.push(item);
    });
  }
  return out;
}

// --- Routes ---

// root -> /home_public (giữ đúng ý đồ redirect của Python)
app.get("/", (req, res) => {
  // Python redirect to 'home_public' (nếu bạn có trang public riêng, thêm route đó)
  return res.redirect("/home");
});

// Login
app.get("/login", (req, res) => {
  res.render("login.html");
});

app.post("/login", async (req, res) => {
  const { username = "", password = "" } = req.body;
  const [rows] = await pool.query(
    "SELECT * FROM accounts WHERE username=? AND password=?",
    [username.trim(), password.trim()]
  );
  const user = rows?.[0];
  if (!user) {
    req.flash("error", "Sai tài khoản hoặc mật khẩu");
    return res.render("login.html", { error: "Sai tài khoản hoặc mật khẩu" });
  }
  req.session.username = user.username;
  req.session.Name = user.Name;
  req.session.role = user.role;
  req.session.lop = user.lop ?? "N/A";
  req.session.tuan = user.tuan ?? "N/A";
  req.session.lop_truc = user.lop_truc ?? "N/A";
  req.flash("success", `Chào mừng ${user.username}! Bạn đã đăng nhập thành công.`);

  if (user.role === "admin") return res.redirect("/home");
  if (user.role === "user") return res.redirect("/user");
  if (user.role === "viewer") return res.redirect("/viewer");
  if (user.role === "giamthi") return res.redirect("/home"); // bám Python
  req.flash("error", "Vai trò không hợp lệ.");
  return res.redirect("/login");
}); // :contentReference[oaicite:3]{index=3}

// Logout
app.get("/logout", loginRequired, (req, res) => {
  req.session.destroy(() => res.redirect("/login"));
});

// /home (admin dashboard + filter tuần/lớp)
app.all("/home", loginRequired, async (req, res) => {
  const role = req.session.role;
  const conn = await pool.getConnection();
  try {
    if (req.method === "POST" && req.body.set_week) {
      if (role === "admin") {
        const selectedWeek = req.body.week_select;
        req.session.tuan = selectedWeek;
        req.flash("info", `Tuần đã được đặt thành ${selectedWeek}.`);
      } else {
        req.flash("error", "Bạn không có quyền thay đổi tuần hiển thị.");
      }
      return res.redirect("/home");
    }

    let study_data = [];
    let rules_data = [];
    if (role === "admin") {
      [study_data] = await conn.query("SELECT * FROM study_data");
      [rules_data] = await conn.query("SELECT * FROM rules_data");
    }

    const lop = req.session.lop ?? "Không xác định";
    const tuan = req.session.tuan ?? "Chưa thiết lập";
    const lop_truc = req.session.lop_truc ?? "Chưa thiết lập";

    // Lấy tuần và lớp trực có trong các bảng (bám Python)
    const [weeks] = await conn.query(
      "SELECT DISTINCT tuan FROM bang_tong_ket UNION SELECT DISTINCT tuan FROM study_data UNION SELECT DISTINCT tuan FROM rules_data ORDER BY tuan ASC"
    );
    const available_export_weeks = weeks.map(r => r.tuan);
    const [classes] = await conn.query(
      "SELECT DISTINCT lop_truc FROM bang_tong_ket UNION SELECT DISTINCT lop_truc FROM study_data UNION SELECT DISTINCT lop_truc FROM rules_data ORDER BY lop_truc ASC"
    );
    const available_export_classes = classes.map(r => r.lop_truc);

    return res.render("home.html", {
      study_data, rules_data, lop, tuan, lop_truc,
      available_export_weeks, available_export_classes
    });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:4]{index=4}

// /user (xem + xóa/sửa theo trạng thái tổng kết)
app.all("/user", loginRequired, async (req, res) => {
  const conn = await pool.getConnection();
  try {
    const user_lop = req.session.lop;
    const user_tuan = req.session.tuan;
    const user_lop_truc = req.session.lop_truc;

    if (req.method === "POST") {
      const { data_id, data_type } = req.body;

      const [[account_status]] = await conn.query(
        "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
        [user_lop_truc, user_tuan]
      );
      const trangthai_tongket = account_status?.trangthai ?? "Chưa tổng kết";
      if (trangthai_tongket === "Đã tổng kết") {
        req.flash("warning", "Không thể chỉnh sửa hoặc xóa dữ liệu vì tuần này đã được tổng kết.");
        return res.redirect("/user");
      }
      if (req.body.delete_data) {
        if (data_type === "study") {
          await conn.query("DELETE FROM study_data WHERE id=?", [data_id]);
          req.flash("success", `Đã xóa dữ liệu học tập ID ${data_id}.`);
        } else if (data_type === "rules") {
          await conn.query("DELETE FROM rules_data WHERE id=?", [data_id]);
          req.flash("success", `Đã xóa dữ liệu nội quy ID ${data_id}.`);
        }
        return res.redirect("/user");
      }
      if (req.body.update_data) {
        if (data_type === "study") return res.redirect(`/update_study_data_admin/${data_id}`);
        if (data_type === "rules") return res.redirect(`/edit_noi_quy/${data_id}`);
      }
    }

    // Hiển thị
    let study_data = [];
    let rules_data = [];
    if (user_lop_truc && user_tuan) {
      [study_data] = await conn.query(
        "SELECT * FROM study_data WHERE lop_truc=? AND tuan=?",
        [user_lop_truc, user_tuan]
      );
      [rules_data] = await conn.query(
        "SELECT * FROM rules_data WHERE lop_truc=? AND tuan=?",
        [user_lop_truc, user_tuan]
      );
    } else {
      req.flash("info", "Thông tin lớp trực hoặc tuần của tài khoản bạn chưa được thiết lập. Vui lòng liên hệ quản trị viên.");
    }

    // Bảng tổng kết (có filter tuan)
    const selected_tuan_tong_ket = req.query.tong_ket_tuan || null;
    const view_all = req.query.view_all === "true";

    const [weeksAll] = await conn.query("SELECT DISTINCT tuan FROM bang_tong_ket ORDER BY tuan ASC");
    const available_weeks_for_lop = weeksAll.map(r => r.tuan);
    const filterTuan = !selected_tuan_tong_ket && available_weeks_for_lop.length && !view_all
      ? available_weeks_for_lop[0]
      : selected_tuan_tong_ket;

    let sql = "SELECT tuan, khoi, lop_truc, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung FROM bang_tong_ket WHERE 1=1";
    const params = [];
    if (filterTuan && !view_all) {
      sql += " AND tuan=?";
      params.push(filterTuan);
    }
    sql += " ORDER BY tuan ASC, khoi ASC, tong_diem_chung DESC";
    const [tong_ket_data_raw] = await conn.query(sql, params);
    const tong_ket_data = rankByWeekAndKhoi(tong_ket_data_raw);

    // trạng thái
    const [[statusRow]] = await conn.query(
      "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
      [user_lop_truc, user_tuan]
    );
    const trangthai_tongket = statusRow?.trangthai ?? "Chưa tổng kết";

    return res.render("user.html", {
      study_data, rules_data,
      lop: user_lop, tuan: user_tuan, lop_truc: user_lop_truc,
      trangthai_tongket,
      tong_ket_data,
      selected_tuan_tong_ket: filterTuan,
      available_weeks_for_lop,
      view_all
    });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:5]{index=5}

// Viewer (role viewer)
app.get("/viewer", loginRequired, async (req, res) => {
  if (req.session.role !== "viewer") {
    req.flash("error", "Bạn không có quyền truy cập trang xem.");
    return res.redirect("/home");
  }
  const conn = await pool.getConnection();
  try {
    const { lop, tuan, lop_truc } = req.session;
    let study_data = [], rules_data = [];
    if (lop && tuan) {
      [study_data] = await conn.query("SELECT * FROM study_data WHERE lop=? AND tuan=?", [lop, tuan]);
      [rules_data] = await conn.query("SELECT * FROM rules_data WHERE lop=? AND tuan=?", [lop, tuan]);
    }
    return res.render("viewer.html", { study_data, rules_data, lop, tuan, lop_truc });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:6]{index=6}

// Học tập
app.all("/hoc_tap", loginRequired, async (req, res) => {
  const role = req.session.role;
  if (!["admin", "giamthi", "user", "viewer"].includes(role)) {
    req.flash("error", "Bạn không có quyền truy cập trang học tập.");
    return res.redirect("/home");
  }
  const conn = await pool.getConnection();
  try {
    const { lop_truc, tuan } = req.session;

    // trạng thái tổng kết
    let trangthai_tongket = "Chưa tổng kết";
    if (lop_truc && tuan) {
      const [[st]] = await conn.query(
        "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
        [lop_truc, tuan]
      );
      if (st) trangthai_tongket = st.trangthai;
    }

    if (req.method === "POST") {
      // delete 1
      if (req.body.delete_data && ["admin", "giamthi"].includes(role)) {
        await conn.query("DELETE FROM study_data WHERE id=?", [req.body.data_id]);
        req.flash("success", `Đã xóa dữ liệu học tập ID ${req.body.data_id}.`);
        return res.redirect("/hoc_tap");
      }
      // truncate
      if (req.body.delete_all && ["admin", "giamthi"].includes(role)) {
        if (req.body.password === "1233") {
          await conn.query("TRUNCATE TABLE study_data");
          req.flash("success", "Đã xóa toàn bộ dữ liệu học tập.");
        } else {
          req.flash("error", "Mật khẩu không đúng. Vui lòng nhập lại.");
        }
        return res.redirect("/hoc_tap");
      }
    }

    let sql = "SELECT * FROM study_data WHERE 1=1";
    const p = [];
    if (role === "user" && lop_truc && tuan) {
      sql += " AND lop_truc=? AND tuan=?";
      p.push(lop_truc, tuan);
    }
    sql += " ORDER BY tuan ASC, lop_truc ASC";
    const [study_data] = await conn.query(sql, p);

    return res.render("hoc_tap.html", { study_data, trangthai_tongket });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:7]{index=7}

// Xóa entry học tập (AJAX)
app.post("/delete_hoc_tap_entry/:id", loginRequired, async (req, res) => {
  const role = req.session.role;
  if (!["admin", "user", "giamthi"].includes(role)) {
    return res.status(403).json({ status: "error", message: "Bạn không có quyền." });
  }
  const conn = await pool.getConnection();
  try {
    const entryId = req.params.id;
    const [[entry]] = await conn.query("SELECT lop, tuan FROM study_data WHERE id=?", [entryId]);
    if (!entry) return res.status(404).json({ status: "error", message: "Dữ liệu không tồn tại." });

    const [[account_status]] = await conn.query(
      "SELECT trangthai FROM accounts WHERE username=? AND tuan=?",
      [req.session.username, entry.tuan]
    );
    if (account_status?.trangthai === "Đã tổng kết") {
      return res.status(403).json({ status: "error", message: "Không thể xóa vì tuần này đã tổng kết." });
    }
    if (role === "user" && entry.lop !== req.session.lop) {
      return res.status(403).json({ status: "error", message: "Bạn không có quyền xóa dữ liệu của lớp khác." });
    }

    await conn.query("DELETE FROM study_data WHERE id=?", [entryId]);
    req.flash("success", "Đã xóa dữ liệu học tập thành công.");
    return res.json({ status: "success", message: "Đã xóa dữ liệu học tập thành công." });
  } catch (e) {
    req.flash("error", `Lỗi: ${e.message}`);
    return res.status(500).json({ status: "error", message: `Lỗi: ${e.message}` });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:8]{index=8}

// Thêm học tập
app.all("/add_hoc_tap", loginRequired, async (req, res) => {
  const role = req.session.role;
  if (!["admin", "giamthi", "user"].includes(role)) {
    req.flash("error", "Bạn không có quyền thêm dữ liệu học tập.");
    return res.redirect("/hoc_tap");
  }
  const conn = await pool.getConnection();
  try {
    const user_lop = req.session.lop || "";
    const user_tuan = req.session.tuan || "";
    // Lấy lớp_trực theo phân công nếu là user
    let user_lop_truc = "";
    if (user_lop && user_tuan) {
      const [[r]] = await conn.query(
        "SELECT lop_truc FROM phan_cong_truc WHERE lop=? AND tuan=?",
        [user_lop, user_tuan]
      );
      user_lop_truc = r?.lop_truc || "Chưa gán";
    }

    // Danh sách lop_truc
    let available_lop_truc = [];
    if (["admin", "giamthi"].includes(role)) {
      const [rows] = await conn.query("SELECT DISTINCT lop_truc FROM phan_cong_truc ORDER BY lop_truc");
      available_lop_truc = rows.map(x => x.lop_truc);
    } else {
      const [rows] = await conn.query(
        "SELECT DISTINCT lop_truc FROM phan_cong_truc WHERE tuan=? ORDER BY lop_truc",
        [user_tuan]
      );
      available_lop_truc = rows.map(x => x.lop_truc);
    }

    // Check tổng kết
    const [[st]] = await conn.query(
      "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
      [user_lop_truc, user_tuan]
    );
    if (st?.trangthai === "Đã tổng kết") {
      req.flash("warning", "Tuần này đã được tổng kết. Bạn không thể thêm dữ liệu học tập.");
      return res.redirect("/hoc_tap");
    }

    if (req.method === "POST") {
      let tuan = user_tuan, lop_truc = user_lop_truc;
      if (["admin", "giamthi"].includes(role)) {
        tuan = (req.body.tuan || "").trim();
        lop_truc = (req.body.lop_truc || "").trim();
      }
      const gio_a = parseInt(req.body.gio_a || 0, 10);
      const gio_b = parseInt(req.body.gio_b || 0, 10);
      const gio_c = parseInt(req.body.gio_c || 0, 10);
      const gio_d = parseInt(req.body.gio_d || 0, 10);
      const dat_kieu_mau = req.body.dat_kieu_mau === "Yes" ? "Yes" : "No";

      let tong_diem = gio_a * 5 + gio_b * -5 + gio_c * -15 + gio_d * -25;
      tong_diem += dat_kieu_mau === "Yes" ? 5 : -10;

      await conn.query(
        `INSERT INTO study_data (tuan, lop, lop_truc, gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [tuan, user_lop, lop_truc, gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem]
      );
      req.flash("success", "Đã thêm dữ liệu học tập thành công.");
      return res.redirect("/hoc_tap");
    }

    return res.render("add_hoc_tap.html", {
      user_lop, user_tuan, user_lop_truc,
      role, available_lop_truc
    });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:9]{index=9}

// Nội quy
app.all("/noi_quy", loginRequired, async (req, res) => {
  const role = req.session.role;
  if (!["admin", "user", "giamthi"].includes(role)) {
    req.flash("error", "Bạn không có quyền truy cập trang nội quy.");
    return res.redirect("/home");
  }
  const conn = await pool.getConnection();
  try {
    const { lop_truc, tuan } = req.session;
    // trạng thái
    let trangthai_tongket = "Chưa tổng kết";
    if (lop_truc && tuan) {
      const [[st]] = await conn.query(
        "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
        [lop_truc, tuan]
      );
      if (st) trangthai_tongket = st.trangthai;
    }

    if (req.method === "POST") {
      if (req.body.delete_data && ["admin", "giamthi"].includes(role)) {
        await conn.query("DELETE FROM rules_data WHERE id=?", [req.body.data_id]);
        req.flash("success", `Đã xóa dữ liệu nội quy ID ${req.body.data_id}.`);
        return res.redirect("/noi_quy");
      }
      if (req.body.delete_all && ["admin", "giamthi"].includes(role)) {
        if (req.body.password === "1233") {
          await conn.query("TRUNCATE TABLE rules_data");
          req.flash("success", "Đã xóa toàn bộ dữ liệu nội quy.");
        } else {
          req.flash("error", "Mật khẩu không đúng. Vui lòng nhập lại.");
        }
        return res.redirect("/noi_quy");
      }
    }

    let sql = "SELECT * FROM rules_data WHERE 1=1";
    const p = [];
    if (role === "user" && lop_truc && tuan) {
      sql += " AND lop_truc=? AND tuan=?";
      p.push(lop_truc, tuan);
    }
    sql += " ORDER BY tuan ASC, lop_truc ASC";
    const [rules_data] = await conn.query(sql, p);

    return res.render("noi_quy.html", { rules_data, trangthai_tongket });
  } finally {
    conn.release();
  }
}); // 【7†source*/

// Sửa nội quy
app.all("/edit_noi_quy/:id", loginRequired, async (req, res) => {
  const conn = await pool.getConnection();
  try {
    const ruleId = req.params.id;
    const [[rule]] = await conn.query("SELECT * FROM rules_data WHERE id=?", [ruleId]);
    if (!rule) {
      req.flash("error", "Không tìm thấy dữ liệu nội quy.");
      return res.redirect("/noi_quy");
    }
    if (req.method === "POST") {
      const tuan = req.body.tuan;
      const lop = req.body.lop;
      const vi_pham = req.body.vi_pham;
      const diem_tru = parseInt(req.body.diem_tru || 0, 10);
      const so_luot = parseInt(req.body.so_luot || 0, 10);
      const hoc_sinh = req.body.hoc_sinh;
      const tong_diem = diem_tru * so_luot;

      await conn.query(
        `UPDATE rules_data
         SET tuan=?, lop=?, noi_dung_vi_pham=?, diem_tru=?, so_luot_vi_pham=?, ten_hoc_sinh_vi_pham=?, tong_diem_vi_pham=?
         WHERE id=?`,
        [tuan, lop, vi_pham, diem_tru, so_luot, hoc_sinh, tong_diem, ruleId]
      );
      req.flash("success", "Cập nhật nội quy thành công!");
      return res.redirect("/noi_quy");
    }
    return res.render("edit_noi_quy.html", { rule });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:10]{index=10}

// Thêm nội quy
app.all("/add_noi_quy", loginRequired, async (req, res) => {
  const role = req.session.role;
  if (!["admin", "giamthi", "user"].includes(role)) {
    req.flash("error", "Bạn không có quyền thêm dữ liệu vi phạm nội quy.");
    return res.redirect("/noi_quy");
  }
  const conn = await pool.getConnection();
  try {
    const [tuanRows] = await conn.query("SELECT DISTINCT tuan FROM phan_cong_truc ORDER BY tuan");
    const available_tuan = tuanRows.map(r => r.tuan);
    const [lopTrucRows] = await conn.query("SELECT DISTINCT lop_truc FROM phan_cong_truc ORDER BY lop_truc");
    const available_lop_truc = lopTrucRows.map(r => r.lop_truc);

    const user_tuan = req.session.tuan || "";
    const user_lop = req.session.lop || "";

    if (req.method === "POST") {
      const tuan = (req.body.tuan || user_tuan || "").trim();
      const lop_truc = (req.body.lop_truc || req.session.lop_truc || "").trim();

      let lop = "";
      if (role === "admin") {
        lop = (req.body.lop || "").trim();
      } else if (role === "giamthi") {
        lop = (req.body.lop || user_lop || "").trim();
      } else {
        lop = user_lop || "";
      }

      const noi_dung_vi_pham = (req.body.vi_pham || "").trim();
      const diem_tru = parseInt(req.body.diem_tru || 0, 10);
      const so_luot = parseInt(req.body.so_luot || 0, 10);
      const hoc_sinh = (req.body.hoc_sinh || "").trim();
      const tong_diem = diem_tru * so_luot;

      await conn.query(
        `INSERT INTO rules_data 
         (tuan, lop, lop_truc, noi_dung_vi_pham, diem_tru, tong_diem_vi_pham, so_luot_vi_pham, ten_hoc_sinh_vi_pham)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [tuan, lop, lop_truc, noi_dung_vi_pham, diem_tru, tong_diem, so_luot, hoc_sinh]
      );
      req.flash("success", "Đã thêm dữ liệu vi phạm nội quy thành công.");
      return res.redirect("/noi_quy");
    }

    return res.render("add_noi_quy.html", {
      role,
      user_tuan,
      available_tuan,
      available_lop_truc,
      lop_truc: req.session.lop_truc || ""
    });
  } finally {
    conn.release();
  }
}); // 【7†source*/

// Cập nhật học tập (admin/giamthi)
app.all("/update_study_data_admin/:id", loginRequired, async (req, res) => {
  if (!["admin", "giamthi"].includes(req.session.role)) {
    req.flash("error", "Bạn không có quyền chỉnh sửa dữ liệu học tập.");
    return res.redirect("/hoc_tap");
  }
  const conn = await pool.getConnection();
  try {
    const dataId = req.params.id;
    const [[study]] = await conn.query("SELECT tuan, lop_truc FROM study_data WHERE id=?", [dataId]);
    if (!study) {
      req.flash("error", "Không tìm thấy dữ liệu học tập.");
      return res.redirect("/hoc_tap");
    }
    const [[st]] = await conn.query(
      "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
      [study.lop_truc, study.tuan]
    );
    if (st?.trangthai === "Đã tổng kết") {
      req.flash("warning", "Không thể chỉnh sửa vì tuần này đã được tổng kết.");
      return res.redirect("/hoc_tap");
    }

    if (req.method === "POST") {
      const gio_a = parseInt(req.body.gio_a || 0, 10);
      const gio_b = parseInt(req.body.gio_b || 0, 10);
      const gio_c = parseInt(req.body.gio_c || 0, 10);
      const gio_d = parseInt(req.body.gio_d || 0, 10);
      const dat_kieu_mau = req.body.dat_kieu_mau === "Yes" ? "Yes" : "No";
      let tong_diem = gio_a * 5 + gio_b * -5 + gio_c * -15 + gio_d * -25;
      tong_diem += dat_kieu_mau === "Yes" ? 5 : -10;

      await conn.query(
        `UPDATE study_data SET gio_a=?, gio_b=?, gio_c=?, gio_d=?, dat_kieu_mau=?, tong_diem=? WHERE id=?`,
        [gio_a, gio_b, gio_c, gio_d, dat_kieu_mau, tong_diem, dataId]
      );
      req.flash("success", "Đã cập nhật dữ liệu học tập thành công.");
      return res.redirect("/hoc_tap");
    }

    const [[data]] = await conn.query("SELECT * FROM study_data WHERE id=?", [dataId]);
    return res.render("update_study_data_admin.html", { data });
  } finally {
    conn.release();
  }
}); // 【7†source*/

// Tổng kết (gồm tổng kết 1 lớp, tất cả lớp, xóa)
app.all("/tong_ket", loginRequired, async (req, res) => {
  if (!["admin", "user", "viewer", "giamthi"].includes(req.session.role)) {
    req.flash("error", "Bạn không có quyền truy cập trang tổng kết.");
    return res.redirect("/home");
  }
  const conn = await pool.getConnection();
  try {
    const { lop_truc: user_lop_truc, tuan: user_tuan, role } = req.session;

    // danh sách lớp chưa tổng kết
    const [not_summarized] = await conn.query(`
      SELECT DISTINCT p.tuan, p.lop_truc
      FROM phan_cong_truc p
      LEFT JOIN bang_tong_ket b
        ON p.tuan = b.tuan AND p.lop_truc = b.lop_truc
      WHERE b.lop_truc IS NULL
      ORDER BY p.tuan, p.lop_truc
    `);
    const available_weeks = [...new Set(not_summarized.map(r => r.tuan))].sort();
    const available_lop_truc = [...new Set(not_summarized.map(r => r.lop_truc))].sort();

    async function tongKetLop(lop_truc, tuan) {
      const [[khoiRow]] = await conn.query(
        "SELECT khoi FROM phan_cong_truc WHERE lop_truc=? AND tuan=?",
        [lop_truc, tuan]
      );
      const khoi = khoiRow?.khoi || "Unknown";
      const [[studySum]] = await conn.query(
        "SELECT SUM(tong_diem) AS total_study_points FROM study_data WHERE tuan=? AND lop_truc=?",
        [tuan, lop_truc]
      );
      const [[ruleSum]] = await conn.query(
        "SELECT SUM(tong_diem_vi_pham) AS total_rules_points FROM rules_data WHERE tuan=? AND lop_truc=?",
        [tuan, lop_truc]
      );
      const total_study_points = studySum?.total_study_points ?? 0;
      const total_rules_points = ruleSum?.total_rules_points ?? 0;
      const tong_diem_chung = total_study_points + total_rules_points;

      await conn.query(
        `INSERT INTO bang_tong_ket (tuan, khoi, lop_truc, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung, trangthai)
         VALUES (?, ?, ?, ?, ?, ?, 'Đã tổng kết')
         ON DUPLICATE KEY UPDATE 
           khoi=VALUES(khoi),
           tong_diem_hoc_tap=VALUES(tong_diem_hoc_tap),
           tong_diem_noi_quy=VALUES(tong_diem_noi_quy),
           tong_diem_chung=VALUES(tong_diem_chung),
           trangthai='Đã tổng kết'`,
        [tuan, khoi, lop_truc, total_study_points, total_rules_points, tong_diem_chung]
      );
    }

    if (req.method === "POST") {
      if (req.body.recalculate) {
        if (role === "user") {
          const [[st]] = await conn.query(
            "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
            [user_lop_truc, user_tuan]
          );
          if (st?.trangthai === "Đã tổng kết") {
            req.flash("warning", `Tuần ${user_tuan} đã được tổng kết cho lớp trực ${user_lop_truc}.`);
          } else if (!user_lop_truc || !user_tuan) {
            req.flash("error", "Bạn cần được gán lớp trực và tuần trước khi tổng kết.");
          } else {
            await tongKetLop(user_lop_truc, user_tuan);
            req.flash("success", `Đã tổng kết thành công cho lớp trực ${user_lop_truc} – Tuần ${user_tuan}.`);
          }
        } else if (["admin", "giamthi"].includes(role)) {
          const lop_truc = req.body.lop_truc;
          const tuan = req.body.tuan;
          if (!lop_truc || !tuan) {
            req.flash("error", "Vui lòng chọn lớp trực và tuần để tổng kết.");
          } else {
            await tongKetLop(lop_truc, tuan);
            req.flash("success", `Đã tổng kết thành công cho lớp trực ${lop_truc} – Tuần ${tuan}.`);
          }
        }
      } else if (req.body.recalculate_all && ["admin", "giamthi"].includes(role)) {
        for (const r of not_summarized) await tongKetLop(r.lop_truc, r.tuan);
        req.flash("success", `Đã tổng kết tất cả ${not_summarized.length} lớp chưa tổng kết.`);
      } else if (req.body.delete_class && ["admin", "giamthi"].includes(role)) {
        await conn.query("DELETE FROM bang_tong_ket WHERE lop_truc=? AND tuan=?", [
          req.body.lop_truc, req.body.tuan
        ]);
        req.flash("success", `Đã xóa dữ liệu tổng kết của lớp ${req.body.lop_truc} cho tuần ${req.body.tuan}.`);
      }
      return res.redirect("/tong_ket");
    }

    // Hiển thị bảng xếp hạng
    const selected_tuan = req.query.tuan || null;
    const selected_khoi = req.query.khoi || null;
    const view_all = req.query.view_all === "true";

    const [weeksAll] = await conn.query("SELECT DISTINCT tuan FROM bang_tong_ket ORDER BY tuan ASC");
    const available_weeks_all = weeksAll.map(r => r.tuan);
    const [khoiAll] = await conn.query("SELECT DISTINCT khoi FROM bang_tong_ket WHERE khoi IS NOT NULL ORDER BY khoi ASC");
    const available_khoi = khoiAll.map(r => r.khoi);

    let sql = `
      SELECT tuan, khoi, lop_truc, tong_diem_hoc_tap, tong_diem_noi_quy, tong_diem_chung, trangthai
      FROM bang_tong_ket WHERE 1=1`;
    const p = [];
    if (selected_tuan && !view_all) { sql += " AND tuan=?"; p.push(selected_tuan); }
    if (selected_khoi) { sql += " AND khoi=?"; p.push(selected_khoi); }
    sql += " ORDER BY tuan ASC, khoi ASC, tong_diem_chung DESC";
    const [rows] = await conn.query(sql, p);
    const data = rankByWeekAndKhoi(rows);

    return res.render("tong_ket.html", {
      data,
      available_weeks: available_weeks,      // lớp chưa tổng kết (giống Python)
      available_lop_truc: available_lop_truc,
      available_khoi,
      selected_tuan,
      selected_khoi,
      trangthai_tongket: (await conn.query(
        "SELECT trangthai FROM bang_tong_ket WHERE lop_truc=? AND tuan=?",
        [user_lop_truc, user_tuan]
      ))[0]?.[0]?.trangthai ?? "Chưa tổng kết"
    });
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:11]{index=11}

// Export danh sách user (Excel) – tương đương /export_accounts
app.get("/export_accounts", loginRequired, async (req, res) => {
  if (req.session.role !== "admin") {
    req.flash("error", "Bạn không có quyền xuất danh sách tài khoản.");
    return res.redirect("/home");
  }
  const tuan = req.query.tuan ? parseInt(req.query.tuan, 10) : null;
  const conn = await pool.getConnection();
  try {
    let sql = `
      SELECT Name, username, password, role, lop, tuan, Capquanli, lop_truc, trangthai
      FROM accounts
      WHERE role='user'`;
    const p = [];
    if (tuan) { sql += " AND tuan=?"; p.push(tuan); }
    const [rows] = await conn.query(sql, p);
    if (!rows.length) {
      req.flash("warning", "Không có dữ liệu tài khoản user để xuất.");
      return res.redirect("/home");
    }

    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet("Accounts_User");
    ws.addRow(Object.keys(rows[0]));
    rows.forEach(r => ws.addRow(Object.values(r)));
    const filename = `danh_sach_user_tuan_${tuan || "all"}.xlsx`;
    res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
    await wb.xlsx.write(res);
    res.end();
  } finally {
    conn.release();
  }
}); // :contentReference[oaicite:12]{index=12}

// Start
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server listening on http://localhost:${PORT}`));
