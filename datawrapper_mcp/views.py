"""MCP App View for inline chart rendering."""

import re
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def get_chart_view_html() -> str:
    """Assemble the View HTML with the vendored SDK inlined.

    Cached so the vendored SDK is read from disk only once.

    The vendored SDK is an ES module that ends with an export statement
    like ``export{...,Uc as App}``. We extract the internal name for App
    and assign it to a global ``window.__McpApp`` so the View code (which
    runs in a separate, non-module script) can access it.
    """
    sdk_js = (_DIR / "vendor" / "ext-apps.js").read_text()

    # Extract the internal name that is exported as App.
    # The export line looks like: export{...,Uc as App}
    match = re.search(r"(\w+) as App\b", sdk_js)
    if not match:
        raise RuntimeError(
            "Could not find 'App' export in vendored ext-apps SDK. "
            "The SDK format may have changed."
        )
    internal_name = match.group(1)

    # Append a global assignment so non-module scripts can access App.
    sdk_js += f"\nwindow.__McpApp = {internal_name};\n"

    return CHART_VIEW_TEMPLATE.replace("/* VENDOR:EXT_APPS_SDK */", sdk_js)


CHART_VIEW_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light dark">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: transparent;
    }
    #chart-container {
      width: 100%;
      min-height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #chart-container img {
      max-width: 100%;
      height: auto;
      border-radius: 4px;
    }
    #chart-container iframe {
      width: 100%;
      height: 400px;
      border: none;
      border-radius: 4px;
    }
    #fallback {
      padding: 2rem;
      text-align: center;
      color: #888;
      font-size: 0.9rem;
    }
    .actions {
      padding: 0.5rem 0.75rem;
      display: flex;
      gap: 0.5rem;
      align-items: center;
      flex-wrap: wrap;
      border-top: 1px solid rgba(128, 128, 128, 0.15);
    }
    .actions button {
      padding: 0.35rem 0.7rem;
      border: 1px solid rgba(128, 128, 128, 0.3);
      border-radius: 4px;
      background: transparent;
      cursor: pointer;
      font-size: 0.8rem;
      color: inherit;
    }
    .actions button:hover {
      background: rgba(128, 128, 128, 0.1);
    }
    .actions button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .chart-id {
      font-size: 0.75rem;
      color: #999;
      margin-left: auto;
      font-family: monospace;
    }
    #status-msg {
      font-size: 0.8rem;
      color: #c90;
      padding: 0.3rem 0.75rem;
    }
    #error-msg {
      font-size: 0.8rem;
      color: #c33;
      padding: 0.3rem 0.75rem;
    }
  </style>
</head>
<body>
  <div id="chart-container">
    <div id="fallback">Waiting for chart data\u2026</div>
  </div>
  <div id="status-msg"></div>
  <div id="error-msg"></div>
  <div class="actions" id="actions" style="display:none">
    <button id="publish-btn">Publish</button>
    <button id="editor-btn">Open in editor \u2197</button>
    <span class="chart-id" id="chart-id-label"></span>
  </div>

  <script type="module">
    /* VENDOR:EXT_APPS_SDK */
  </script>
  <script>
    // Wait for the module script above to execute and set window.__McpApp
    document.addEventListener("DOMContentLoaded", function() {
      // Module scripts are deferred, so __McpApp is available after DOMContentLoaded
      setTimeout(function() { initChartView(); }, 0);
    });

    function initChartView() {
      var AppClass = window.__McpApp;
      if (!AppClass) {
        document.getElementById("chart-container").innerHTML =
          '<div id="fallback">Error: MCP App SDK failed to load.</div>';
        return;
      }

      // State
      var currentChartId = null;
      var currentEditUrl = null;
      var isPublished = false;
      var currentPngBase64 = null;
      var embedLoadTimeout = null;

      // DOM refs
      var container = document.getElementById("chart-container");
      var actions = document.getElementById("actions");
      var publishBtn = document.getElementById("publish-btn");
      var editorBtn = document.getElementById("editor-btn");
      var chartIdLabel = document.getElementById("chart-id-label");
      var statusMsg = document.getElementById("status-msg");
      var errorMsg = document.getElementById("error-msg");

      function clearMessages() {
        statusMsg.textContent = "";
        errorMsg.textContent = "";
      }

      function showError(msg) {
        errorMsg.textContent = msg;
      }

      function showStatus(msg) {
        statusMsg.textContent = msg;
      }

      function showPngPreview(base64Data) {
        var img = document.createElement("img");
        img.src = "data:image/png;base64," + base64Data;
        img.alt = "Chart preview";
        container.replaceChildren(img);
      }

      function showEmbed(chartId, cacheBust) {
        var url = "https://datawrapper.dwcdn.net/" + chartId + "/";
        if (cacheBust) {
          url += "?v=" + Date.now();
        }

        var iframe = document.createElement("iframe");
        iframe.src = url;
        iframe.title = "Datawrapper chart";
        iframe.allow = "fullscreen";
        container.replaceChildren(iframe);

        var embedLoaded = false;
        if (embedLoadTimeout) clearTimeout(embedLoadTimeout);

        window.addEventListener("message", function onMessage(event) {
          if (typeof event.data === "object" && event.data["datawrapper-height"]) {
            embedLoaded = true;
            var heights = event.data["datawrapper-height"];
            var chartHeight = Object.values(heights)[0];
            if (chartHeight && iframe.parentNode) {
              iframe.style.height = chartHeight + "px";
            }
          }
        });

        embedLoadTimeout = setTimeout(function() {
          if (!embedLoaded) {
            if (currentPngBase64) {
              showPngPreview(currentPngBase64);
              showStatus("Embed not available yet. Showing static preview.");
            } else {
              container.innerHTML =
                '<div id="fallback">Embed not available yet. Try re-publishing.</div>';
            }
          }
        }, 8000);

        isPublished = true;
        publishBtn.textContent = "Re-publish";
      }

      function showUnpublished() {
        if (currentPngBase64) {
          showPngPreview(currentPngBase64);
        } else {
          container.innerHTML =
            '<div id="fallback">Chart created. Click <strong>Publish</strong> to enable the interactive view.</div>';
        }
        isPublished = false;
        publishBtn.textContent = "Publish";
      }

      function handleToolResult(content) {
        clearMessages();

        if (!content || !Array.isArray(content)) return;

        var textBlock = null;
        var imageBlock = null;
        for (var i = 0; i < content.length; i++) {
          if (content[i].type === "text") textBlock = content[i];
          if (content[i].type === "image") imageBlock = content[i];
        }

        if (!textBlock) return;

        var data;
        try {
          data = JSON.parse(textBlock.text);
        } catch (e) {
          container.innerHTML = '<div id="fallback">Error parsing chart data</div>';
          return;
        }

        if (imageBlock && imageBlock.data) {
          currentPngBase64 = imageBlock.data;
        }

        var wasPublished = isPublished;
        currentChartId = data.chart_id;
        currentEditUrl = data.edit_url;

        chartIdLabel.textContent = currentChartId;
        actions.style.display = "flex";

        if (wasPublished && data.message && data.message.indexOf("updated") !== -1) {
          showUnpublished();
          isPublished = false;
          publishBtn.textContent = "Re-publish";
          showStatus("Chart updated. Re-publish to update the live embed.");
        } else if (data.public_url) {
          showEmbed(currentChartId, false);
        } else {
          showUnpublished();
        }
      }

      // Initialize the MCP App
      var app = new AppClass({
        name: "Datawrapper Chart View",
        version: "1.0.0",
      });

      app.ontoolresult = function(result) {
        handleToolResult(result.content);
      };

      publishBtn.addEventListener("click", function() {
        if (!currentChartId) return;
        clearMessages();
        publishBtn.disabled = true;
        var originalText = publishBtn.textContent;
        publishBtn.textContent = "Publishing\u2026";

        app.callServerTool({
          name: "publish_chart",
          arguments: { chart_id: currentChartId },
        }).then(function() {
          showEmbed(currentChartId, true);
          clearMessages();
        }).catch(function(e) {
          var msg = (e && e.message) ? e.message : "Unknown error";
          showError("Publish failed: " + msg);
          publishBtn.textContent = originalText;
        }).finally(function() {
          publishBtn.disabled = false;
        });
      });

      editorBtn.addEventListener("click", function() {
        if (!currentEditUrl) return;
        try {
          app.sendOpenLink(currentEditUrl);
        } catch (e) {
          editorBtn.textContent = currentEditUrl;
          editorBtn.style.userSelect = "all";
          editorBtn.style.cursor = "text";
        }
      });

      app.connect();
    }
  </script>
</body>
</html>"""
