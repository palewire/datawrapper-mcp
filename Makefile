datawrapper-mcp.tar:
	docker build -t datawrapper-mcp --platform linux/amd64 --file Dockerfile .
	docker save -o datawrapper-mcp.tar datawrapper-mcp:latest

clean:
	rm -f datawrapper-mcp.tar
