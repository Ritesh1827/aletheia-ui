/* TrustTrace code scanner — dedicated reusable module.
 *
 * Uses html5-qrcode (bundled locally at /static/js/vendor/) for in-browser
 * decoding of QR codes, EAN-13, EAN-8, UPC-A, UPC-E and Code 128. Camera
 * access happens only after an explicit user gesture. No frames or images
 * ever leave the device: only the decoded text string is handed to the
 * verification form.
 *
 * Single-session guard: one Html5Qrcode instance at a time, duplicate
 * decoded values ignored while a session is open.
 */

(function () {
  "use strict";

  var LIB_URL = "/static/js/vendor/html5-qrcode.min.js";
  var libPromise = null;
  var libRetries = 0;
  var scanner = null;
  var sessionOpen = false;
  var lastValue = null;
  var lastAt = 0;

  function loadLibrary() {
    if (window.Html5Qrcode) return Promise.resolve();
    if (libPromise) return libPromise;
    libPromise = new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = LIB_URL + "?v=2.3.8";
      s.async = true;
      s.onload = function () {
        libRetries = 0;
        resolve();
      };
      s.onerror = function () {
        libPromise = null;
        libRetries += 1;
        reject(new Error("Scanner library failed to load from this server"
          + (libRetries > 1 ? " (attempt " + libRetries + ")" : "")
          + ". Reload the page and press Start again, or type the serial manually."));
      };
      document.head.appendChild(s);
    });
    return libPromise;
  }

  function supportedFormats() {
    if (!window.Html5QrcodeSupportedFormats) return [];
    var F = window.Html5QrcodeSupportedFormats;
    return [F.QR_CODE, F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E, F.CODE_128];
  }

  function stopScanner() {
    if (!scanner) return Promise.resolve();
    var inst = scanner;
    scanner = null;
    try {
      return inst.stop().then(function () {
        try { inst.clear(); } catch (e) { /* noop */ }
      }).catch(function () { /* already stopped */ });
    } catch (e) {
      return Promise.resolve();
    }
  }

  function closeSession() {
    sessionOpen = false;
    lastValue = null;
    return stopScanner();
  }

  function listCameras() {
    return window.Html5Qrcode.getCameras().catch(function () { return []; });
  }

  function describeError(err) {
    var msg = String((err && err.message) || err || "");
    if (/permission|not allowed|denied/i.test(msg)) {
      return "Camera permission was denied. Allow camera access for this site, or type the serial manually.";
    }
    if (/not found|no camera|no device/i.test(msg)) {
      return "No camera was found on this device. Type the serial manually instead.";
    }
    if (/secure|https|localhost/i.test(msg)) {
      return "Camera access needs a secure context (localhost or HTTPS). Type the serial manually instead.";
    }
    if (/in use|already/i.test(msg)) {
      return "The camera is already in use by another tab or app. Close it and retry, or type the serial manually.";
    }
    return "The camera could not start (" + msg + "). Type the serial manually instead.";
  }

  function ensureSecureContext() {
    if (window.isSecureContext) return null;
    return "This page is not a secure context, so the browser blocks camera access. "
      + "Serve over localhost or HTTPS, or type the serial manually.";
  }

  window.TrustTraceScanner = {
    formatsLabel: "QR · EAN-13 · EAN-8 · UPC-A · UPC-E · Code 128",
    isOpen: function () { return sessionOpen; },

    open: function (opts) {
      opts = opts || {};
      var onDecode = opts.onDecode || function () {};
      var onError = opts.onError || function () {};
      if (sessionOpen) return Promise.resolve(false);
      var insecure = ensureSecureContext();
      if (insecure) {
        onError(insecure);
        return Promise.resolve(false);
      }
      sessionOpen = true;
      lastValue = null;
      return loadLibrary().then(function () {
        if (!sessionOpen) return false;
        var config = {
          fps: 10,
          qrbox: { width: 240, height: 180 },
          aspectRatio: 4 / 3,
          formatsToSupport: supportedFormats(),
        };
        scanner = new window.Html5Qrcode(opts.regionId || "scan-region");
        var request = { facingMode: "environment" };
        if (opts.deviceId) request = { deviceId: { exact: opts.deviceId } };
        return scanner.start(
          request,
          config,
          function (decodedText) {
            var now = Date.now();
            if (decodedText === lastValue && now - lastAt < 1500) return;
            lastValue = decodedText;
            lastAt = now;
            onDecode(decodedText);
          },
          function () { /* per-frame misses are routine; stay silent */ }
        ).then(function () { return true; }).catch(function (err) {
          sessionOpen = false;
          onError(describeError(err));
          return stopScanner().then(function () { return false; });
        });
      }).catch(function (err) {
        sessionOpen = false;
        onError(describeError(err));
        return false;
      });
    },

    cameras: function () {
      return loadLibrary().then(listCameras, function () { return []; });
    },

    close: closeSession,
  };

  window.addEventListener("pagehide", closeSession);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) closeSession();
  });
})();
