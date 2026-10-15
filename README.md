# File and Document Management System (Web App)

A web-based File and Document Management System built with **Python** and **Streamlit**, developed as a semester output for **Data Structures and Algorithms (DSA)**. The system manages 500 document records stored in JSON and uses custom-implemented data structures and algorithms instead of built-in library shortcuts.

**Live Demo:** https://mz.sisko.replit.dev

---

## Features

- **Search:** Find documents quickly by name.
- **Sort:** Order documents by Name, Size, or Date Modified.
- **Edit:** Update a document's name, folder path, file type, and description.
- **Archive:** Soft-delete documents and restore them when needed.
- **Version History:** View previous versions of a document and track changes over time.
- **Browse Folders:** Navigate the nested folder structure and view the documents inside each folder.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language  | Python 3 |
| Web Framework | Streamlit |
| Data Storage | JSON (500 document records) |

---

## Custom Data Structures

| Data Structure | Purpose |
|----------------|---------|
| **DocumentHashTable** | Stores documents using separate chaining for fast lookup by ID. |
| **FolderTree** | Represents the nested folder hierarchy using `FolderNode` objects. |
| **VersionStack** | Keeps a LIFO history of document versions for tracking and restoring edits. |

## Custom Algorithms

| Algorithm | Purpose |
|-----------|---------|
| **Merge Sort** | Sorts documents by name, size, or date without using Python's built-in `.sort()`. |
| **Depth-First Search (DFS)** | Traverses and searches the nested folder tree. |

---

## System Architecture

```
Streamlit UI  →  Python Logic Layer  →  JSON Storage
                 (Hash Table, Folder Tree,
                  Version Stack, Merge Sort, DFS)
```

---

## Complexity Analysis

| Operation | Structure / Algorithm | Time Complexity | Space Complexity |
|-----------|-----------------------|-----------------|------------------|
| Document lookup | DocumentHashTable | O(1) average, O(n) worst | O(n) |
| Folder traversal | FolderTree + DFS | O(V + E) | O(V) |
| Save / restore version | VersionStack (push/pop) | O(1) | O(n) |
| Sort documents | Merge Sort | O(n log n) | O(n) |

---

## How to Run

1. **Install Python** (version 3.9 or higher) from [python.org](https://www.python.org/downloads/).

2. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd <your-repository-folder>
   ```

3. **Install Streamlit:**
   ```bash
   pip install streamlit
   ```

4. **Run the application:**
   ```bash
   streamlit run main.py
   ```

5. Open the local URL shown in the terminal (usually `http://localhost:8501`).

---

## Dataset

- 500 document records stored in JSON
- 5 folders and 3 file types
- Largest folder: `DSA` (334 documents)

---

## Limitations and Future Work

- **Limitations:** Local JSON storage is not suitable for concurrent multi-user access, and free-tier hosting may cause cold-start delays.
- **Future Work:** Migrate to MySQL or PostgreSQL, add user authentication, support real file uploads, and deploy on a dedicated cloud server.

---

## Author

**Stephen Evangelista**
Individual Project, Data Structures and Algorithms (DSA)
