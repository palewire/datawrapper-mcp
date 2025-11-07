FROM python:3.11-slim

# Create deployment user and group
RUN groupadd -g 1234 deploymentgroup && \
    useradd -u 1234 -g deploymentgroup -m -s /bin/bash deployment

# Set working directory
WORKDIR /app

# Copy application code
COPY ./datawrapper_mcp /app/datawrapper_mcp
COPY ./deployment /app/deployment

# Install dependencies
RUN pip install --no-cache-dir -r /app/deployment/requirements.txt

# Set ownership
RUN chown -R deployment:deploymentgroup /app

# Switch to deployment user
USER deployment

# Set environment variables (can be overridden at runtime)
ENV MCP_SERVER_HOST=0.0.0.0
ENV MCP_SERVER_PORT=8501
ENV MCP_SERVER_NAME=datawrapper-mcp

# Expose the server port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/healthz')"

# Run the HTTP server
CMD ["python", "-m", "deployment.app"]
