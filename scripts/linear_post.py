#!/usr/bin/env python3
"""Linear helper: post comments and upload screenshots to issues.

Usage:
  python3 linear_post.py comment THE-41 "body text"
  python3 linear_post.py image THE-41 /path/to/shot.png "optional caption"
  python3 linear_post.py status THE-41 <stateName>   # e.g. "In Progress", "Done"

Uploads images via Linear's fileUpload mutation -> PUT to signed URL -> embed
the asset URL as markdown in a comment so it renders inline on the issue.
"""
import os, sys, json, mimetypes, urllib.request

def _key():
    k = os.environ.get("LINEAR_API_KEY", "")
    if not k:
        envf = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(envf):
            for line in open(envf):
                if line.startswith("LINEAR_API_KEY"):
                    k = line.split("=", 1)[1].strip()
    if not k:
        raise SystemExit("LINEAR_API_KEY not found")
    return k

KEY = _key()
API = "https://api.linear.app/graphql"

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body,
        headers={"Authorization": KEY, "Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req))
    if "errors" in resp:
        raise SystemExit("GraphQL error: " + json.dumps(resp["errors"]))
    return resp["data"]

def issue_id(identifier):
    d = gql("query($id:String!){ issue(id:$id){ id } }", {"id": identifier})
    return d["issue"]["id"]

def post_comment(identifier, body):
    iid = issue_id(identifier)
    gql("mutation($i:CommentCreateInput!){ commentCreate(input:$i){ success } }",
        {"i": {"issueId": iid, "body": body}})
    print(f"comment posted to {identifier}")

def upload_image(identifier, path, caption=""):
    iid = issue_id(identifier)
    size = os.path.getsize(path)
    ctype = mimetypes.guess_type(path)[0] or "image/png"
    name = os.path.basename(path)
    # 1) request a signed upload URL
    d = gql("""mutation($ct:String!,$fn:String!,$sz:Int!){
        fileUpload(contentType:$ct, filename:$fn, size:$sz){
            success uploadFile{ uploadUrl assetUrl headers{ key value } }
        }}""", {"ct": ctype, "fn": name, "sz": size})
    uf = d["fileUpload"]["uploadFile"]
    upload_url = uf["uploadUrl"]
    asset_url = uf["assetUrl"]
    # 2) PUT the bytes to the signed URL with required headers
    data = open(path, "rb").read()
    put = urllib.request.Request(upload_url, data=data, method="PUT")
    put.add_header("Content-Type", ctype)
    for h in uf["headers"]:
        put.add_header(h["key"], h["value"])
    r = urllib.request.urlopen(put)
    if r.status not in (200, 201, 204):
        raise SystemExit(f"upload PUT failed: {r.status}")
    # 3) embed the asset URL in a comment as markdown
    body = (caption + "\n\n" if caption else "") + f"![{name}]({asset_url})"
    gql("mutation($i:CommentCreateInput!){ commentCreate(input:$i){ success } }",
        {"i": {"issueId": iid, "body": body}})
    print(f"image uploaded + posted to {identifier}: {asset_url}")

def set_status(identifier, state_name):
    iid = issue_id(identifier)
    # find the workflow state id by name for this issue's team
    d = gql("""query($id:String!){ issue(id:$id){ team{ states{ nodes{ id name } } } } }""",
            {"id": identifier})
    states = d["issue"]["team"]["states"]["nodes"]
    match = [s for s in states if s["name"].lower() == state_name.lower()]
    if not match:
        raise SystemExit(f"state '{state_name}' not found. Available: {[s['name'] for s in states]}")
    gql("mutation($id:String!,$s:String!){ issueUpdate(id:$id,input:{stateId:$s}){ success } }",
        {"id": iid, "s": match[0]["id"]})
    print(f"{identifier} -> {state_name}")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "comment":
        post_comment(sys.argv[2], sys.argv[3])
    elif cmd == "image":
        upload_image(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "status":
        set_status(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit("unknown command")
