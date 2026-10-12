/* Verify-page scan wiring: modal lifecycle, decode handling, form handoff.
 * Depends on window.TrustTraceScanner (static/js/scanner.js), loaded lazily
 * on first Scan click. No-ops gracefully when elements are absent.
 */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  function init() {
    var openBtn = $("scan-open");
    var modal = $("scan-modal");
    var startBtn = $("scan-start");
    var stopBtn = $("scan-stop");
    var useBtn = $("scan-use");
    var closeBtn = $("scan-close");
    var closeX = $("scan-close-x");
    var statusEl = $("scan-status");
    var decodedBox = $("scan-decoded");
    var decodedValue = $("scan-decoded-value");
    var decodedNote = $("scan-decoded-note");
    var camWrap = $("scan-cam-wrap");
    var camSelect = $("scan-camera");
    var form = $("verify-form");
    var serialInput = $("serial");
    if (!openBtn || !modal) return;

    var lastOpener = null;
    var decoded = null;
    var starting = false;

    function setStatus(msg) {
      if (statusEl) statusEl.textContent = msg;
    }

    function setRunning(running) {
      if (startBtn) startBtn.disabled = running;
      if (stopBtn) stopBtn.disabled = !running;
    }

    function showModal() {
      lastOpener = document.activeElement;
      modal.hidden = false;
      document.body.style.overflow = "hidden";
      setStatus("Camera is off. Press Start to begin.");
      if (startBtn) startBtn.focus();
      loadCameras();
    }

    function hideModal() {
      stopCamera(true);
      modal.hidden = true;
      document.body.style.overflow = "";
      if (lastOpener && lastOpener.focus) lastOpener.focus();
    }

    function loadCameras() {
      if (!window.TrustTraceScanner || !camWrap || !camSelect) return;
      window.TrustTraceScanner.cameras().then(function (cams) {
        if (!cams || cams.length < 2) {
          camWrap.hidden = true;
          return;
        }
        camSelect.innerHTML = "";
        cams.forEach(function (c, i) {
          var opt = document.createElement("option");
          opt.value = c.id;
          opt.textContent = c.label || ("Camera " + (i + 1));
          camSelect.appendChild(opt);
        });
        var back = cams.findIndex(function (c) {
          return /back|rear|environment/i.test(c.label || "");
        });
        if (back >= 0) camSelect.selectedIndex = back;
        camWrap.hidden = false;
      });
    }

    function startCamera() {
      if (starting || !window.TrustTraceScanner) {
        if (!window.TrustTraceScanner) {
          var tag = document.createElement("script");
          tag.src = "/static/js/scanner.js";
          tag.onload = startCamera;
          tag.onerror = function () {
            setStatus("Scanner script failed to load. Type the serial manually instead.");
          };
          document.head.appendChild(tag);
        }
        return;
      }
      starting = true;
      setStatus("Starting camera…");
      var deviceId = camSelect && !camWrap.hidden ? camSelect.value : null;
      window.TrustTraceScanner.open({
        deviceId: deviceId,
        onDecode: function (text) {
          decoded = text;
          if (decodedValue) decodedValue.textContent = text;
          if (decodedNote) {
            decodedNote.textContent = "Scanned — review the value, then use it or close and edit the field.";
          }
          if (decodedBox) decodedBox.hidden = false;
          if (useBtn) useBtn.disabled = false;
          setStatus("Code captured. Review it below, then use it or scan again.");
          window.TrustTraceScanner.close();
          setRunning(false);
          starting = false;
          if (useBtn) useBtn.focus();
        },
        onError: function (msg) {
          setStatus(msg);
          setRunning(false);
          starting = false;
        },
      }).then(function (ok) {
        starting = false;
        if (ok) {
          setRunning(true);
          setStatus("Camera live — hold a QR or barcode inside the frame. Formats: " +
            window.TrustTraceScanner.formatsLabel + ".");
        }
      });
    }

    function stopCamera(silent) {
      starting = false;
      setRunning(false);
      if (window.TrustTraceScanner) window.TrustTraceScanner.close();
      if (!silent) setStatus("Camera stopped.");
    }

    function useDecoded() {
      if (!decoded) return;
      var target = (serialInput && serialInput.closest("form")) || form;
      if (serialInput) {
        var nativeSetter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype, "value").set;
        nativeSetter.call(serialInput, decoded);
        serialInput.dispatchEvent(new Event("input", { bubbles: true }));
        serialInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
      hideModal();
      if (window.toast) window.toast("Scanned value placed in the lookup field.");
      if (target) target.requestSubmit();
    }

    openBtn.addEventListener("click", showModal);
    closeBtn.addEventListener("click", hideModal);
    if (closeX) closeX.addEventListener("click", hideModal);
    startBtn.addEventListener("click", startCamera);
    stopBtn.addEventListener("click", function () { stopCamera(false); });
    useBtn.addEventListener("click", useDecoded);
    modal.addEventListener("click", function (ev) {
      if (ev.target === modal) hideModal();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !modal.hidden) hideModal();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
