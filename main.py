import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List
from pathlib import Path
from fastapi.responses import FileResponse


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow all domains (you can change the list for more control)
origins = [
    "*"
]

# Add CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Allow specific HTTP methods
    allow_headers=["X-Custom-Header"],  # Allow specific headers
)
# Fichier JSON où les informations des cours seront stockées
COURSES_FILE = "courses.json"
UPLOAD_DIR = "pdf_files"

# Assurez-vous que le répertoire pour les fichiers PDF existe
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

# Modèle Pydantic pour la validation des données d'un cours
class Course(BaseModel):
    name: str
    description: str
    pdf_path: str
    created_at: datetime
    updated_at: datetime
    level: str  # Nouveau champ pour le niveau du cours (5ème, 6ème, Bac)

# Fonction pour lire les cours depuis le fichier JSON
def read_courses():
    if os.path.exists(COURSES_FILE):
        try:
            with open(COURSES_FILE, "r") as file:
                # Essayer de charger le contenu JSON
                return json.load(file)
        except json.JSONDecodeError:
            # Si le fichier est vide ou mal formaté, retourner une liste vide
            return []
    return []

# Fonction pour écrire les cours dans le fichier JSON
def write_courses(courses: List[Course]):
    # Créer le fichier si nécessaire
    if not os.path.exists(COURSES_FILE):
        with open(COURSES_FILE, "w") as file:
            json.dump([], file)  # Initialisation avec une liste vide
    
    # Convertir en dictionnaires uniquement si ce sont des objets Course
    courses_data = [course.dict() if isinstance(course, Course) else course for course in courses]
    
    with open(COURSES_FILE, "w") as file:
        json.dump(courses_data, file, default=str, indent=4)

# CRUD: Créer un nouveau cours avec téléchargement de PDF
@app.post("/courses/", response_model=Course)
async def create_course(
    name: str = Form(...),
    description: str = Form(...),
    level: str = Form(...),  # Paramètre pour le niveau du cours
    file: UploadFile = File(...),
):
    # Vérifier que le fichier est un PDF
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    
    # Créer un chemin pour le fichier PDF
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Sauvegarder le fichier PDF dans le répertoire
    with open(pdf_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Créer l'objet cours avec les informations nécessaires
    course = Course(
        name=name,
        description=description,
        level=level,  # Niveau ajouté
        pdf_path=pdf_path,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # Lire les cours existants et les ajouter au nouveau cours
    courses = read_courses()
    courses.append(course)
    write_courses(courses)
    
    return course

# CRUD: Lire tous les cours
@app.get("/courses/", response_model=List[Course])
async def get_courses():
    return read_courses()

# CRUD: Lire un cours par son nom
@app.get("/courses/{course_name}", response_model=Course)
async def get_course(course_name: str):
    courses = read_courses()
    for course in courses:
        if course["name"] == course_name:
            return course
    raise HTTPException(status_code=404, detail="Course not found")

# CRUD: Mettre à jour un cours
@app.put("/courses/{course_name}", response_model=Course)
async def update_course(course_name: str, updated_course: Course):
    courses = read_courses()
    for index, course in enumerate(courses):
        if course["name"] == course_name:
            updated_course.created_at = course["created_at"]  # Garder la date de création
            updated_course.updated_at = datetime.now()  # Mettre à jour la date
            courses[index] = updated_course
            write_courses(courses)
            return updated_course
    raise HTTPException(status_code=404, detail="Course not found")

# CRUD: Supprimer un cours
@app.delete("/courses/{course_name}", response_model=Course)
async def delete_course(course_name: str):
    courses = read_courses()
    for index, course in enumerate(courses):
        if course["name"] == course_name:
            deleted_course = courses.pop(index)
            write_courses(courses)
            return deleted_course
    raise HTTPException(status_code=404, detail="Course not found")


@app.get("/courses/{course_name}/download")
async def download_course_file(course_name: str):
    # Lire la liste des cours existants
    courses = read_courses()
    
    # Rechercher le cours par son nom
    for course in courses:
        if course["name"] == course_name:
            # Vérifier si le fichier existe
            file_path = course["pdf_path"]
            if os.path.exists(file_path):
                # Retourner le fichier PDF
                return FileResponse(file_path, media_type="application/pdf", filename=Path(file_path).name)
            else:
                raise HTTPException(status_code=404, detail="Fichier PDF non trouvé")
    
    # Si le cours n'est pas trouvé
    raise HTTPException(status_code=404, detail="Cours non trouvé")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
