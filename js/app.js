/* ==========================================================================
   Oxford School & College Sundovi - Scholarship Test Result 2026
   Vanilla JavaScript, no dependencies.
   ========================================================================== */
(function () {
  "use strict";

  document.documentElement.classList.add("js");

  var CLASSES = ["3rd", "4th", "5th", "6th", "7th", "8th", "9th"];
  var CONTACTS = ["03437199137", "03451595458"];
  var NO_MATCH = "No result found. Please check the roll number or student name and try again.";
  var LOAD_ERROR = "Unable to load results at the moment. Please try again later.";

  var cache = null;
  var pending = null;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function clear(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function norm(value) {
    return String(value == null ? "" : value)
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }

  function digits(value) {
    return String(value == null ? "" : value).replace(/\s+/g, "");
  }

  function ordinal(number) {
    var n = Number(number);
    if (!isFinite(n)) return String(number == null ? "—" : number);
    var suffix = "th";
    if (n % 100 < 11 || n % 100 > 13) {
      suffix = n % 10 === 1 ? "st" : n % 10 === 2 ? "nd" : n % 10 === 3 ? "rd" : "th";
    }
    return n + suffix;
  }

  function percent(value) {
    return value == null ? "—" : Number(value).toFixed(2) + "%";
  }

  function reducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function loadResults() {
    if (cache) return Promise.resolve(cache);
    if (pending) return pending;
    pending = fetch("data/results.json", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (!data || !Array.isArray(data.students)) throw new Error("Invalid data file");
        cache = data;
        return data;
      })
      .finally(function () {
        pending = null;
      });
    return pending;
  }

  /* ------------------------------------------------------------------ */
  /* Header, navigation, reveal animations                               */
  /* ------------------------------------------------------------------ */

  function initHeader() {
    var header = document.getElementById("site-header");
    var toggle = document.getElementById("menu-toggle");
    var nav = document.getElementById("primary-nav");

    if (toggle && nav) {
      function closeMenu() {
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Open navigation menu");
        nav.classList.remove("is-open");
      }
      toggle.addEventListener("click", function () {
        var open = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!open));
        toggle.setAttribute("aria-label", open ? "Open navigation menu" : "Close navigation menu");
        nav.classList.toggle("is-open", !open);
      });
      nav.addEventListener("click", function (event) {
        if (event.target.closest("a")) closeMenu();
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") closeMenu();
      });
    }

    if (header) {
      var onScroll = function () {
        header.classList.toggle("is-scrolled", window.scrollY > 8);
      };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }

    var sectionLinks = Array.prototype.slice.call(
      document.querySelectorAll(".nav-link[data-section]")
    );
    if (sectionLinks.length && "IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            sectionLinks.forEach(function (link) {
              link.classList.toggle("is-active", link.getAttribute("data-section") === entry.target.id);
            });
          });
        },
        { rootMargin: "-28% 0px -62% 0px" }
      );
      ["home", "result", "toppers", "gallery", "contact"].forEach(function (id) {
        var section = document.getElementById(id);
        if (section) observer.observe(section);
      });
    }
  }

  function initReveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
    if (!("IntersectionObserver" in window) || reducedMotion()) {
      items.forEach(function (item) { item.classList.add("is-visible"); });
      return;
    }
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" }
    );
    items.forEach(function (item) { observer.observe(item); });
  }

  /* ------------------------------------------------------------------ */
  /* Statistics                                                          */
  /* ------------------------------------------------------------------ */

  function animateCount(node, target) {
    if (reducedMotion() || !window.requestAnimationFrame) {
      node.textContent = String(target);
      return;
    }
    var duration = 1100;
    var start = performance.now();
    function frame(now) {
      var progress = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - progress, 3);
      node.textContent = String(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function initStats() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-stat]"));
    if (!nodes.length) return;
    loadResults().then(function (data) {
      var statistics = data.meta && data.meta.statistics ? data.meta.statistics : {};
      nodes.forEach(function (node) {
        var value = Number(statistics[node.getAttribute("data-stat")]);
        animateCount(node, isFinite(value) ? value : 0);
      });
    }).catch(function () {
      nodes.forEach(function (node) { node.textContent = "—"; });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Result search                                                       */
  /* ------------------------------------------------------------------ */

  var URDU = {
    first: "شاندار کارکردگی! آپ نے پہلی پوزیشن حاصل کی اور 100% اسکالرشپ جیتی۔",
    second: "زبردست کامیابی! آپ نے دوسری پوزیشن حاصل کی اور 60% اسکالرشپ جیتی۔",
    third: "احسن کامیابی! آپ نے تیسری پوزیشن حاصل کی اور 40% اسکالرشپ جیتی۔",
    winnerNote: "اسکالرشپ اور داخلے کی کارروائی کے لیے براہِ کرم اپنا نتیجہ کارڈ لے کر اسکول آفس رابطہ کریں۔",
    pass: "مبارک ہو! آپ نے اسکالرشپ ٹیسٹ میں اچھی کارکردگی دکھائی۔ داخلے اور مزید معلومات کے لیے براہِ کرم اسکول آفس رابطہ کریں۔",
    appeared: "اسکالرشپ ٹیسٹ میں حصہ لینے کا شکریہ۔ داخلے اور مزید معلومات کے لیے براہِ کرم اسکول آفس رابطہ کریں۔",
    absent: "آپ اسکالرشپ ٹیسٹ میں حاضر نہیں ہوئے۔ داخلے اور مزید معلومات کے لیے براہِ کرم اسکول آفس رابطہ کریں۔"
  };

  function initSearch() {
    var rollForm = document.getElementById("roll-form");
    if (!rollForm) return;

    var nameForm = document.getElementById("name-form");
    var rollInput = document.getElementById("roll-input");
    var nameInput = document.getElementById("name-input");
    var statusBox = document.getElementById("search-status");
    var matchList = document.getElementById("match-list");
    var output = document.getElementById("result-output");
    var panel = document.querySelector(".search-panel");
    var tabs = Array.prototype.slice.call(document.querySelectorAll(".search-tab"));

    function clearFeedback() {
      clear(statusBox);
      statusBox.hidden = true;
      statusBox.className = "search-status";
      clear(matchList);
      matchList.hidden = true;
    }

    function feedback(message, kind, retry) {
      clearFeedback();
      statusBox.className = "search-status" + (kind ? " is-" + kind : "");
      statusBox.appendChild(el("p", null, message));
      if (retry) {
        var button = el("button", "btn btn--ghost", "Retry");
        button.type = "button";
        button.addEventListener("click", retry);
        statusBox.appendChild(button);
      }
      statusBox.hidden = false;
    }

    function selectTab(selected) {
      tabs.forEach(function (tab) {
        var active = tab === selected;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        var target = document.getElementById(tab.getAttribute("aria-controls"));
        if (target) target.hidden = !active;
      });
      clearFeedback();
      resetShownResult();
      (selected.id === "tab-roll" ? rollInput : nameInput).focus();
    }

    tabs.forEach(function (tab, index) {
      tab.addEventListener("click", function () { selectTab(tab); });
      tab.addEventListener("keydown", function (event) {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        var next = tabs[(index + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        selectTab(next);
        next.focus();
      });
    });

    Array.prototype.slice.call(document.querySelectorAll("[data-clear]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var field = button.getAttribute("data-clear") === "roll" ? rollInput : nameInput;
        field.value = "";
        field.focus();
        clearFeedback();
      });
    });

    function withData(callback) {
      statusBox.hidden = true;
      return loadResults().then(callback).catch(function () {
        feedback(LOAD_ERROR, "error", function () { withData(callback); });
      });
    }

    function showMatches(matches, meta, query) {
      clear(output);
      document.body.classList.remove("has-result");
      clear(matchList);
      matchList.appendChild(el("h3", null, "Multiple students found. Please select the correct student."));
      var intro = el("p", "field-hint", "Showing " + matches.length + " result" + (matches.length === 1 ? "" : "s") + " for “" + query + "”.");
      matchList.appendChild(intro);
      matches.forEach(function (student) {
        var button = el("button", "match-item");
        button.type = "button";
        button.appendChild(el("strong", null, student.name));
        button.appendChild(el("span", null, "Class " + student.class + "  ·  Roll No. " + student.rollNo + "  ·  " + student.status));
        button.addEventListener("click", function () {
          clearFeedback();
          renderCertificate(student, meta);
          output.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
        });
        matchList.appendChild(button);
      });
      matchList.hidden = false;
    }

    function presentResult(matches, meta, query, selectionMode) {
      clearFeedback();
      if (matches.length === 1) {
        renderCertificate(matches[0], meta);
        output.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
      } else if (matches.length > 1 && selectionMode) {
        showMatches(matches.slice(0, 50), meta, query);
      } else if (matches.length > 1) {
        showMatches(matches.slice(0, 50), meta, query);
      } else {
        feedback(NO_MATCH, "error");
      }
    }

    function resetShownResult() {
      clear(output);
      document.body.classList.remove("has-result");
    }

    rollForm.addEventListener("submit", function (event) {
      event.preventDefault();
      resetShownResult();
      var query = digits(rollInput.value);
      if (!query) {
        feedback("Please enter a roll number.", "error");
        rollInput.focus();
        return;
      }
      withData(function (data) {
        var matches = data.students.filter(function (student) {
          return digits(student.rollNo) === query;
        });
        presentResult(matches, data.meta, rollInput.value.trim(), true);
      });
    });

    nameForm.addEventListener("submit", function (event) {
      event.preventDefault();
      resetShownResult();
      var query = norm(nameInput.value);
      if (query.length < 2) {
        feedback("Please enter at least two characters of the student name.", "error");
        nameInput.focus();
        return;
      }
      withData(function (data) {
        var matches = data.students.filter(function (student) {
          return norm(student.name).indexOf(query) !== -1;
        });
        presentResult(matches, data.meta, nameInput.value.trim(), true);
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Certificate                                                         */
  /* ------------------------------------------------------------------ */

  function detail(label, value) {
    var box = el("div", "detail-item");
    box.appendChild(el("span", "detail-item__label", label));
    box.appendChild(el("span", "detail-item__value", value));
    return box;
  }

  function markBox(label, value) {
    var box = el("div", "mark-box");
    box.appendChild(el("span", "mark-box__label", label));
    box.appendChild(el("span", "mark-box__value", value));
    return box;
  }

  function positionCard(label, value, variant, note) {
    var card = el("div", "position-card" + (variant ? " position-card--" + variant : ""));
    card.appendChild(el("span", "position-card__label", label));
    card.appendChild(el("span", "position-card__value", value));
    if (note) card.appendChild(el("span", "position-card__note", note));
    return card;
  }

  function addUrdu(parent, text) {
    var node = el("p", "urdu", text);
    node.setAttribute("lang", "ur");
    node.setAttribute("dir", "rtl");
    parent.appendChild(node);
  }

  function confetti(container) {
    if (reducedMotion()) return;
    var wrap = el("div", "confetti");
    wrap.setAttribute("aria-hidden", "true");
    var colors = ["#D4A843", "#174A7E", "#2E8B57", "#C8813A", "#F2D897"];
    for (var i = 0; i < 28; i += 1) {
      var piece = el("i");
      piece.style.left = (Math.random() * 98).toFixed(1) + "%";
      piece.style.background = colors[i % colors.length];
      piece.style.setProperty("--delay", (Math.random() * 1.2).toFixed(2) + "s");
      piece.style.setProperty("--duration", (2.2 + Math.random() * 1.4).toFixed(2) + "s");
      piece.style.setProperty("--drift", Math.round((Math.random() - 0.5) * 180) + "px");
      wrap.appendChild(piece);
    }
    container.appendChild(wrap);
    window.setTimeout(function () {
      if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
    }, 4000);
  }

  function renderCertificate(student, meta) {
    var output = document.getElementById("result-output");
    if (!output) return;
    clear(output);

    var eventTitle = (meta && meta.event) || "Scholarship Test Result 2026";
    var schoolName = (meta && meta.institution) || "Oxford School & College Sundovi";
    var isAbsent = student.status === "Absent";
    var isWinner = !!student.scholarship;
    var variant = "neutral";

    if (isAbsent) variant = "grey";
    else if (isWinner && student.scholarship === "100%") variant = "gold";
    else if (isWinner && student.scholarship === "60%") variant = "silver";
    else if (isWinner && student.scholarship === "40%") variant = "bronze";
    else if (student.status === "Pass") variant = "green";

    var certificate = el("article", "certificate certificate--" + variant);
    certificate.setAttribute("aria-label", "Result card for " + student.name);

    var header = el("header", "certificate__header");
    var logoPlate = el("span", "certificate__logo");
    var logo = el("img");
    logo.src = "assets/logo.png";
    logo.alt = "Oxford School & College Sundovi logo";
    logo.width = 48;
    logo.height = 48;
    logoPlate.appendChild(logo);
    header.appendChild(logoPlate);

    var school = el("div", "certificate__school");
    school.appendChild(el("strong", null, schoolName));
    school.appendChild(el("span", null, eventTitle));
    header.appendChild(school);

    var badgeText = isAbsent
      ? "Absent"
      : isWinner
        ? ordinal(student.classPosition) + " Position · " + student.scholarship + " Scholarship"
        : student.status;
    header.appendChild(el("span", "certificate__badge", badgeText));
    certificate.appendChild(header);

    var body = el("div", "certificate__body");
    body.appendChild(el("p", "certificate__title", "Scholarship Test Result 2026"));
    body.appendChild(el("h3", "certificate__student", student.name));

    var details = el("div", "detail-grid");
    if (student.fatherName) details.appendChild(detail("Father / Guardian", student.fatherName));
    details.appendChild(detail("Class", student.class));
    details.appendChild(detail("Roll Number", student.rollNo));
    if (student.school) details.appendChild(detail("Previous School", student.school));
    body.appendChild(details);

    if (!isAbsent) {
      var marks = el("div", "marks-grid");
      marks.appendChild(markBox("Total Marks", student.total));
      marks.appendChild(markBox("Obtained Marks", student.obtained));
      marks.appendChild(markBox("Percentage", percent(student.percentage)));
      body.appendChild(marks);

      var positions = el("div", "positions");
      positions.appendChild(
        positionCard("Class-wise Position", ordinal(student.classPosition),
          isWinner ? variant : null, "Within Class " + student.class)
      );
      positions.appendChild(
        positionCard("Overall Position", ordinal(student.overallPosition), null,
          "Across Classes 3rd to 9th")
      );
      body.appendChild(positions);

      if (student.scholarship) {
        body.appendChild(el("p", "scholarship-line",
          "Scholarship Awarded: " + student.scholarship + " · Class-wise " + ordinal(student.classPosition) + " position"));
      }
    }

    var message = el("div", "certificate__message");
    var english = "";
    var urdu = "";
    var heading = "Result Message";

    if (isAbsent) {
      heading = "Absent in the Test";
      english = "You did not appear in the scholarship test. For admission and further information, please contact the school office.";
      urdu = URDU.absent;
    } else if (isWinner && student.classPosition === 1) {
      heading = "Congratulations!";
      english = "Excellent performance! You secured 1st position in Class " + student.class + " and won a 100% scholarship.";
      urdu = URDU.first;
    } else if (isWinner && student.classPosition === 2) {
      heading = "Congratulations!";
      english = "Great achievement! You secured 2nd position in Class " + student.class + " and won a 60% scholarship.";
      urdu = URDU.second;
    } else if (isWinner && student.classPosition === 3) {
      heading = "Congratulations!";
      english = "Well done! You secured 3rd position in Class " + student.class + " and won a 40% scholarship.";
      urdu = URDU.third;
    } else if (student.status === "Pass") {
      english = "Congratulations on your result! Thank you for participating in the scholarship test. You are welcome to take admission in Oxford School & College Sundovi. For admission and further information, please contact the school office.";
      urdu = URDU.pass;
    } else {
      english = "Thank you for taking part in the scholarship test. You are welcome to take admission in Oxford School & College Sundovi. For admission and further information, please contact the school office.";
      urdu = URDU.appeared;
    }

    message.appendChild(el("h3", null, heading));
    message.appendChild(el("p", null, english));
    if (isWinner) {
      message.appendChild(el("p", null,
        "Please contact the school office with this result card for admission and scholarship formalities."));
      addUrdu(message, urdu);
      addUrdu(message, URDU.winnerNote);
    } else {
      addUrdu(message, urdu);
    }
    body.appendChild(message);

    var contact = el("p", "certificate__contact");
    contact.appendChild(document.createTextNode("Admission and result enquiries: "));
    CONTACTS.forEach(function (number, index) {
      if (index) contact.appendChild(document.createTextNode(" · "));
      var link = el("a", null, number);
      link.href = "tel:" + number;
      link.setAttribute("dir", "ltr");
      contact.appendChild(link);
    });
    body.appendChild(contact);
    body.appendChild(el("small", "certificate__developer", "Developed by Usama Khan"));

    var actions = el("div", "certificate__actions no-print");
    var print = el("button", "btn btn--primary", "Print / Download Result");
    print.type = "button";
    print.addEventListener("click", function () { window.print(); });
    actions.appendChild(print);

    var share = el("button", "btn btn--gold", "Share Result on WhatsApp");
    share.type = "button";
    share.addEventListener("click", function () { shareOnWhatsApp(student, meta); });
    actions.appendChild(share);

    var again = el("button", "btn btn--ghost", "Search Another Result");
    again.type = "button";
    again.addEventListener("click", function () {
      clear(output);
      document.body.classList.remove("has-result");
      var roll = document.getElementById("roll-input");
      if (roll) {
        roll.value = "";
        roll.focus();
      }
      if (panel) panel.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
    });
    actions.appendChild(again);
    body.appendChild(actions);

    certificate.appendChild(body);
    output.appendChild(certificate);
    document.body.classList.add("has-result");
    if (isWinner) confetti(certificate);
  }

  function shareOnWhatsApp(student, meta) {
    var schoolName = (meta && meta.institution) || "Oxford School & College Sundovi";
    var eventTitle = (meta && meta.event) || "Scholarship Test 2026";
    var site = window.location.origin + window.location.pathname;
    var lines = [
      schoolName + " - " + eventTitle,
      "Student: " + student.name,
      "Roll No: " + student.rollNo,
      "Class: " + student.class
    ];
    if (student.status === "Absent") {
      lines.push("Status: Absent in the test");
    } else {
      lines.push("Obtained Marks: " + student.obtained + " / " + student.total);
      lines.push("Percentage: " + percent(student.percentage));
      lines.push("Class-wise Position: " + ordinal(student.classPosition));
      lines.push("Overall Position: " + ordinal(student.overallPosition));
      if (student.scholarship) lines.push("Scholarship: " + student.scholarship);
    }
    lines.push("Result: " + site);
    window.open("https://wa.me/?text=" + encodeURIComponent(lines.join("\n")), "_blank", "noopener,noreferrer");
  }

  /* ------------------------------------------------------------------ */
  /* Toppers                                                             */
  /* ------------------------------------------------------------------ */

  function initToppers() {
    var grid = document.getElementById("toppers-grid");
    if (!grid) return;

    loadResults().then(function (data) {
      clear(grid);
      var stats = (data.meta && data.meta.statistics && data.meta.statistics.classes) || [];
      stats.forEach(function (classStat) {
        if (!classStat.toppers || !classStat.toppers.length) return;
        var classCard = el("article", "topper-class reveal");
        var head = el("div", "topper-class__header");
        head.appendChild(el("h3", null, "Class " + classStat.class));
        head.appendChild(el("p", null, "Congratulations to our top three position holders."));
        classCard.appendChild(head);

        var list = el("div", "topper-list");
        classStat.toppers.forEach(function (topper) {
          var position = topper.classPosition;
          var variant = position === 1 ? "" : position === 2 ? " silver" : " bronze";
          var card = el("article", "topper-card" + variant);
          card.appendChild(el("p", "topper-card__position", ordinal(position) + " Position"));
          card.appendChild(el("h4", "topper-card__name", topper.name));

          var full = data.students.find(function (student) {
            return student.rollNo === topper.rollNo && student.class === classStat.class;
          });
          if (full && full.fatherName) card.appendChild(el("p", "topper-card__meta", "Father / Guardian: " + full.fatherName));
          if (full && full.school) card.appendChild(el("p", "topper-card__meta", "School: " + full.school));
          card.appendChild(el("p", "topper-card__meta", "Roll No: " + topper.rollNo));

          var statsRow = el("div", "topper-card__stats");
          statsRow.appendChild(el("span", null, topper.marks + " marks"));
          statsRow.appendChild(el("span", null, percent(full ? full.percentage : null)));
          statsRow.appendChild(el("span", null, "Overall " + ordinal(topper.overallPosition)));
          card.appendChild(statsRow);

          var scholarshipCount = classStat.toppers.filter(function (item) {
            return item.classPosition === position && item.scholarship;
          }).length;
          var tied = classStat.toppers.filter(function (item) {
            return item.classPosition === position;
          }).length > 1;

          if (topper.scholarship) {
            card.appendChild(el("p", "topper-card__scholarship", topper.scholarship + " Scholarship"));
          } else {
            card.appendChild(el("p", "topper-card__scholarship topper-card__review",
              tied || !scholarshipCount ? "Scholarship under management review" : "Scholarship under review"));
          }
          list.appendChild(card);
        });
        classCard.appendChild(list);
        grid.appendChild(classCard);
      });
      if (!grid.children.length) grid.appendChild(el("p", "loading-note", "Toppers will be published here shortly."));
      initReveal();
    }).catch(function () {
      clear(grid);
      grid.appendChild(el("p", "loading-note", LOAD_ERROR));
    });
  }

  /* ------------------------------------------------------------------ */
  /* Gallery lightbox                                                    */
  /* ------------------------------------------------------------------ */

  function initGallery() {
    var items = Array.prototype.slice.call(document.querySelectorAll(".gallery-item"));
    var dialog = document.getElementById("lightbox");
    if (!items.length || !dialog || typeof dialog.showModal !== "function") return;

    var image = document.getElementById("lightbox-image");
    var caption = document.getElementById("lightbox-caption");
    var index = 0;

    function show(next) {
      index = (next + items.length) % items.length;
      var img = items[index].querySelector("img");
      var cap = items[index].querySelector("figcaption");
      image.src = img.getAttribute("src");
      image.alt = img.getAttribute("alt") || "";
      caption.textContent = cap ? cap.textContent.trim() : "";
    }

    items.forEach(function (item, position) {
      item.setAttribute("role", "button");
      item.setAttribute("tabindex", "0");
      item.setAttribute("aria-label", "Open photo " + (position + 1) + " of " + items.length);
      item.addEventListener("click", function () {
        show(position);
        dialog.showModal();
      });
      item.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        show(position);
        dialog.showModal();
      });
    });

    document.getElementById("lightbox-close").addEventListener("click", function () { dialog.close(); });
    document.getElementById("lightbox-prev").addEventListener("click", function () { show(index - 1); });
    document.getElementById("lightbox-next").addEventListener("click", function () { show(index + 1); });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") show(index - 1);
      if (event.key === "ArrowRight") show(index + 1);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Class results table                                                 */
  /* ------------------------------------------------------------------ */

  function initClasses() {
    var body = document.getElementById("class-table-body");
    if (!body) return;

    var tabs = Array.prototype.slice.call(document.querySelectorAll(".class-tab"));
    var search = document.getElementById("table-search");
    var clearButton = document.getElementById("table-clear");
    var count = document.getElementById("table-count");
    var errorBox = document.getElementById("table-error");
    var headers = Array.prototype.slice.call(document.querySelectorAll(".result-table thead th"));
    var sortButtons = Array.prototype.slice.call(document.querySelectorAll(".result-table th button"));

    var currentClass = "3rd";
    var sortKey = "rollNo";
    var sortDir = "asc";
    var data = null;

    function cell(text, className) {
      var td = el("td", className || null, text);
      return td;
    }

    function render() {
      if (!data) return;
      var rows = data.students.filter(function (student) { return student.class === currentClass; });
      var query = norm(search.value);
      var filtered = query
        ? rows.filter(function (student) {
            return norm(student.name).indexOf(query) !== -1 ||
              digits(student.rollNo).indexOf(digits(query)) !== -1;
          })
        : rows;

      var sorted = filtered.slice().sort(function (a, b) {
        var aAbsent = a.obtained == null ? 1 : 0;
        var bAbsent = b.obtained == null ? 1 : 0;
        if (aAbsent !== bAbsent) return aAbsent - bAbsent;
        var av = a[sortKey];
        var bv = b[sortKey];
        if (typeof av === "string" || typeof bv === "string") {
          var result = String(av == null ? "" : av).localeCompare(
            String(bv == null ? "" : bv), undefined, { numeric: true, sensitivity: "base" }
          );
          return sortDir === "asc" ? result : -result;
        }
        av = av == null ? Infinity : av;
        bv = bv == null ? Infinity : bv;
        return sortDir === "asc" ? av - bv : bv - av;
      });

      clear(body);
      if (!sorted.length) {
        var empty = el("tr");
        empty.appendChild(cell(query ? NO_MATCH : "No results available for this class.", "table-placeholder"));
        empty.firstChild.colSpan = 6;
        body.appendChild(empty);
      }

      sorted.forEach(function (student) {
        var tr = el("tr", student.obtained == null ? "row-absent" : null);
        tr.appendChild(cell(student.rollNo));
        tr.appendChild(cell(student.name));
        tr.appendChild(cell(student.obtained == null ? "Absent" : String(student.obtained), "num"));
        tr.appendChild(cell(percent(student.percentage), "num"));
        tr.appendChild(cell(student.obtained == null ? "—" : ordinal(student.classPosition), "num"));
        tr.appendChild(cell(student.obtained == null ? "—" : ordinal(student.overallPosition), "num"));
        body.appendChild(tr);
      });

      count.textContent = "Showing " + sorted.length + " of " + rows.length +
        " students in Class " + currentClass + ".";
      headers.forEach(function (th) {
        var button = th.querySelector("button");
        th.setAttribute("aria-sort", button && button.dataset.sort === sortKey
          ? (sortDir === "asc" ? "ascending" : "descending")
          : "none");
      });
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        currentClass = tab.dataset.class;
        tabs.forEach(function (item) {
          var active = item === tab;
          item.classList.toggle("is-active", active);
          item.setAttribute("aria-selected", String(active));
        });
        render();
      });
    });

    sortButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        var key = button.dataset.sort;
        if (sortKey === key) sortDir = sortDir === "asc" ? "desc" : "asc";
        else { sortKey = key; sortDir = "asc"; }
        render();
      });
    });

    search.addEventListener("input", render);
    clearButton.addEventListener("click", function () {
      search.value = "";
      search.focus();
      render();
    });

    loadResults().then(function (loaded) {
      data = loaded;
      render();
    }).catch(function () {
      errorBox.hidden = false;
      errorBox.textContent = LOAD_ERROR;
      count.textContent = "";
      clear(body);
      var tr = el("tr");
      var td = el("td", "table-placeholder", LOAD_ERROR);
      td.colSpan = 6;
      tr.appendChild(td);
      body.appendChild(tr);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Boot                                                                */
  /* ------------------------------------------------------------------ */

  function boot() {
    initHeader();
    initReveal();
    initStats();
    initSearch();
    initToppers();
    initGallery();
    initClasses();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
