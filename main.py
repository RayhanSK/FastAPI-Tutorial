

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from datetime import datetime, timezone
from typing import Annotated, Any, Generic, Optional, TypeVar

from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Field, SQLModel, Session, create_engine, select
class Campaign(SQLModel,table=True):
    campaign_id: int|None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    due_date: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=True, index=True)
class CampaignCreate(SQLModel):
    name: str
    due_date: datetime | None = None

sqlite_file_name="database.db"
sqlite_url=f"sqlite:///{sqlite_file_name}"
connect_args={"check_same_thread":False}
engine=create_engine(sqlite_url,connect_args=connect_args)
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
def get_session():
    with Session(engine) as session:
        yield session
SessionDep=Annotated[Session,Depends(get_session)]
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        if not session.exec(select(Campaign)).first():
            session.add_all([
                Campaign(name="Rayhan",due_date=datetime.now()),
                Campaign(name="Zaiba",due_date=datetime.now()),
                Campaign(name="Saira",due_date=datetime.now())
            ])
            session.commit()
    yield
app=FastAPI(root_path="/api/v1",lifespan=lifespan)
T=TypeVar("T")
class Response(BaseModel,Generic[T]):
    data:T
class PaginatedResponse(BaseModel,Generic[T]):
    count: int
    data: T
    next: Optional[str]
    previous: Optional[str] 

@app.get("/campaigns",response_model=PaginatedResponse[list[Campaign]])
async def read_campaings(session: SessionDep,request:Request,page: int = Query(1, ge=1),page_size: int = Query(5, ge=1, le=100)):
    limit=page_size
    offset=(page-1)*limit
    campaigns=session.exec(select(Campaign).order_by(Campaign.campaign_id).offset(offset).limit(limit)).all() #type: ignore
    base_url=str(request.url).split("?")[0]
    total=session.exec(select(func.count()).select_from(Campaign)).one()
    if offset+limit<total:
        next_url=f"{base_url}?page={page+1}&page_size={page_size}"
    else:
        next_url=None
    if page>1:
        prev_url=f"{base_url}?page={page-1}&page_size={page_size}"
    else:
        prev_url=None

    return {
        "count":total,
        "data":campaigns,
        "next":next_url,
        "previous":prev_url
        }
@app.get("/campaigns/{id}",response_model=Response[Campaign])
async def read_campaign(id: int,session: SessionDep):
    campaign=session.get(Campaign, id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"data":campaign}
@app.post("/campaigns",status_code=201,response_model=Response[list[Campaign]])
async def create_campaign(campaign: list[CampaignCreate],session: SessionDep):
    db_campaigns=[]
    for c in campaign:
        db_campaign=Campaign.model_validate(c)
        session.add(db_campaign)
        db_campaigns.append(db_campaign)
    session.commit()
    for c in db_campaigns:
        session.refresh(c)
    return {"data":db_campaigns}
@app.put("/campaigns/{id}",response_model=Response[Campaign])
async def update_campaign(id: int, campaign: CampaignCreate, session: SessionDep):
    db_campaign = session.get(Campaign, id)
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    db_campaign.name = campaign.name
    db_campaign.due_date = campaign.due_date
    session.add(db_campaign)
    session.commit()
    session.refresh(db_campaign)
    return {"data": db_campaign}
@app.delete("/campaigns/{id}",status_code=204)
async def delete_campaign(id: int, session: SessionDep):
    db_campaign = session.get(Campaign, id)
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    session.delete(db_campaign)
    session.commit()
    return Response(status_code=204)
"""data:Any = [
    {"id":1,"name":"Rayhan","due_date":datetime.now(),"created_at":datetime.now()},
    {"id":2,"name":"Zaiba","due_date":datetime.now(),"created_at":datetime.now()},
    {"id":3,"name":"Saira","due_date":datetime.now(),"created_at":datetime.now()},
    {"id":4,"name":"Anwar","due_date":datetime.now(),"created_at":datetime.now()},
    {"id":5,"name":"Sadia","due_date":datetime.now(),"created_at":datetime.now()},
]
@app.get("/")
async def root():
    return {"message":"Hello World"}
@app.get("/campaigns")
async def read_campaigns():
    return {"campaigns":data}
@app.get("/campaigns/{id}")
async def read_campaign(id: int):
    for campaign in data:
        if campaign["id"] == id:
            return {"campaign": campaign}
    raise HTTPException(status_code=404, detail="Campaign not found")
@app.post("/campaigns")
async def create_campaign(body: dict[str,Any]):
    new_campaign: Any = {
        "id": len(data) + 1,
        "name": body.get("name"),
        "due_date": datetime.now(),
        "created_at": datetime.now()
    }
    data.append(new_campaign)
    return {"campaign": new_campaign}
@app.put("/campaigns/{id}")
async def update_campaign(id: int, body:dict[str,Any]):
    for index,campaign in enumerate(data):
        if campaign["id"]==id:
            updated_campaign: Any ={

                "id": id,
                "name": body.get("name"),
                "due_date": campaign.get("due_date"),
                "created_at": campaign.get("created_at")
            }
            data[index]=updated_campaign
            return {"campaign": updated_campaign}
    raise HTTPException(status_code=404, detail="Campaign not found")
@app.delete("/campaigns/{id}")
async def delete_campaign(id: int):
    for index,campaign in enumerate(data):
        if campaign["id"]==id:
            data.pop(index)
            return Response(status_code=204)
    raise HTTPException(status_code=404, detail="Campaign not found")

"""