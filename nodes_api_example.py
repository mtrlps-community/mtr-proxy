from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()


class Node(BaseModel):
    hostname: str
    ip: str
    port: int


@app.get("/api/nodes", response_model=List[Node])
def get_nodes():
    return [
        Node(hostname="node1", ip="1.1.1.1", port=25565),
        Node(hostname="node2", ip="2.2.2.2", port=25565),
    ]


class Announcement(BaseModel):
    id: str
    title: str
    content: str


@app.get("/api/announcement", response_model=Announcement)
def get_announcement():
    return Announcement(
        id="2026-01",
        title="系统公告",
        content="欢迎使用新版代理",
    )
