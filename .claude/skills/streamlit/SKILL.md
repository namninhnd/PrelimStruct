# Streamlit App Development

**MUST USE** for creating interactive Python web apps, dashboards, and data applications.

## Overview

Streamlit is a Python library for creating interactive web applications. It provides:
- Fast prototyping with minimal code
- Automatic UI generation from Python scripts
- Real-time updates and interactive widgets
- Built-in support for data visualization

## Quick Start

### 1. Installation

```bash
pip install streamlit
```

**Verify installation:**
```bash
streamlit --version
```

### 2. Create Your First App

```python
# app.py
import streamlit as st

st.title("My First App")
st.write("Hello, World!")

name = st.text_input("What's your name?")
if name:
    st.write(f"Hello, {name}!")
```

### 3. Run the App

```bash
streamlit run app.py
```

## Project Structure Best Practices

### Recommended Layout
```
my_streamlit_app/
├── app.py                    # Main entry point
├── pages/                    # Multipage apps (optional)
│   ├── 1_📊_Dashboard.py
│   └── 2_⚙️_Settings.py
├── src/
│   ├── ui/                  # UI components
│   │   ├── components.py    # Reusable UI elements
│   │   ├── sidebar.py       # Sidebar configuration
│   │   └── theme.py         # Custom styling
│   ├── core/                # Data models
│   ├── services/            # Business logic
│   └── utils/               # Helper functions
├── requirements.txt          # Dependencies
├── .streamlit/
│   ├── config.toml          # App configuration
│   └── secrets.toml         # API keys (gitignored)
└── README.md
```

**Source**: Pattern validated in PrelimStruct v3-5 (production structural design platform)

## Core Concepts

### 1. Rerun Model

**Every interaction reruns the entire script from top to bottom.**

```python
# This runs on every interaction
import streamlit as st

st.title("Counter")

# ❌ DON'T: This resets every time
count = 0
if st.button("Increment"):
    count += 1
st.write(f"Count: {count}")  # Always shows 1

# ✅ DO: Use session state
if 'count' not in st.session_state:
    st.session_state.count = 0

if st.button("Increment"):
    st.session_state.count += 1
st.write(f"Count: {st.session_state.count}")
```

### 2. Widget Keys

**Always use unique keys when creating widgets in loops or conditionally:**

```python
# ❌ DON'T: Duplicate keys cause errors
for i in range(3):
    st.text_input("Enter value")  # All have same key

# ✅ DO: Unique keys
for i in range(3):
    st.text_input(f"Value {i}", key=f"input_{i}")
```

## State Management

### 1. Session State Initialization

**Initialize all state variables at app start:**

```python
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_data': None,
        'processed_files': set(),
        'chat_history': [],
        'model_config': {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Call at app start
init_session_state()
```

### 2. Session State Across Pages

Session state is **globally shared** across all pages:

```python
# page1.py
st.session_state['shared_data'] = "value"

# page2.py  
st.write(st.session_state['shared_data'])  # ✅ Works
```

### 3. State Reset Pattern

```python
# Detect changes and reset dependent state
previous_id = st.session_state.get('previous_id', None)
current_id = st.text_input("Enter ID")

if current_id != previous_id:
    st.session_state.messages = []  # Reset messages
    st.session_state.previous_id = current_id
    st.rerun()  # Trigger rerun with clean state
```

## Caching Strategies

### 1. st.cache_data

Use for: Data loading, transformations, API calls

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(dataset: str) -> pd.DataFrame:
    """Results are serialized (pickled)"""
    return pd.read_csv(f"data/{dataset}.csv")

@st.cache_data
def expensive_computation(params):
    return process_data(params)
```

**Key characteristics:**
- Serializes return values (pickle)
- Safe for DataFrames, primitives, JSON-serializable objects
- Use `ttl` for time-based invalidation
- Thread-safe

### 2. st.cache_resource

Use for: Database connections, ML models, global resources

```python
@st.cache_resource
def get_database_connection():
    """Returns same object instance - shared across sessions"""
    return create_connection()

@st.cache_resource
def load_model():
    """Load model once, share across all users"""
    return torch.load("model.pth")
```

**Key characteristics:**
- Does NOT serialize (returns same object)
- Use for: connections, models, large objects
- Shared globally across users

### 3. Session-Scoped Caching

```python
@st.cache_data(scope="session")
def user_specific_data(user_id):
    """Cached per session, not globally"""
    return fetch_user_data(user_id)
```

## UI/Layout Patterns

### 1. Page Configuration (Must be FIRST command)

```python
st.set_page_config(
    page_title="My App",
    page_icon="🎈",
    layout="wide",  # or "centered"
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.streamlit.io',
        'Report a bug': "https://github.com/...",
        'About': "My awesome app!"
    }
)
```

**Rules:**
- Call once per page
- Must be FIRST Streamlit command
- Cannot be called inside callback

### 2. Columns for Layouts

```python
# Equal width columns
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Temperature", "72°F", "2%")
with col2:
    st.metric("Pressure", "30.2 in", "-4%")

# Variable width (relative numbers)
left, middle, right = st.columns([0.6, 0.3, 0.1])

# Columns with borders
col1, col2 = st.columns(2, border=True)
```

### 3. Sidebar Configuration

```python
with st.sidebar:
    st.title("⚙️ Settings")
    
    # API Configuration
    api_key = st.text_input("API Key", type="password")
    
    # Model Selection
    model = st.selectbox("Model", ["gpt-4", "claude-3"])
    
    # Advanced Settings
    with st.expander("Advanced"):
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
    
    st.divider()
    st.info("💡 Tip: Check docs for help")
```

### 4. Forms for Batch Input

```python
with st.form("user_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")
    age = st.number_input("Age", min_value=0)
    
    submitted = st.form_submit_button("Submit")
    
    if submitted:
        # Process all inputs together
        save_user(name, email, age)
```

**Benefits:**
- Prevents reruns on each widget interaction
- Better UX for multi-field inputs
- Keyboard shortcut: Enter to submit

### 5. Progress Indicators

```python
# Simple spinner
with st.spinner("Processing..."):
    result = expensive_function()

# Progress bar
progress_bar = st.progress(0)
status_text = st.empty()

for i, item in enumerate(items):
    status_text.text(f"Processing {item}...")
    process(item)
    progress_bar.progress((i + 1) / len(items))

status_text.text("Done!")

# Status messages
st.success("✅ Success!")
st.error("❌ Error occurred")
st.warning("⚠️ Warning message")
st.info("ℹ️ Information")
```

## Multipage Apps

### 1. Directory-Based Pages (Streamlit 1.10+)

```
app.py                    # Entrypoint
pages/
├── 1_📊_Dashboard.py    # Numbers prefix for ordering
├── 2_📈_Analytics.py
└── 3_⚙️_Settings.py
```

- Automatic navigation sidebar
- Emoji icons in filenames
- Numbered prefixes control order

### 2. Dynamic Navigation with st.navigation

```python
import streamlit as st

# Define pages
login_page = st.Page(login, title="Log in", icon=":material/login:")
dashboard = st.Page("reports/dashboard.py", title="Dashboard", default=True)
settings = st.Page("admin/settings.py", title="Settings")

# Conditional navigation based on auth
if st.session_state.logged_in:
    pg = st.navigation({
        "Account": [logout_page],
        "Reports": [dashboard, bugs, alerts],
        "Tools": [search, history]
    })
else:
    pg = st.navigation([login_page])

pg.run()
```

## Configuration & Secrets

### 1. App Configuration (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true

[logger]
level = "info"
```

### 2. Secrets Management (.streamlit/secrets.toml)

```toml
# .streamlit/secrets.toml (DO NOT COMMIT - add to .gitignore)

# Root-level become environment variables
DATABASE_URL = "postgresql://..."
API_KEY = "sk-..."

# Sections for structured access
[database]
host = "localhost"
port = 5432
username = "admin"

[api]
openai_key = "sk-..."
```

```python
# Access in Python
import streamlit as st

# Root level
api_key = st.secrets["API_KEY"]

# Section-based
db_host = st.secrets["database"]["host"]
openai_key = st.secrets["api"]["openai_key"]
```

**For Streamlit Cloud**: Add secrets via UI (Settings → Secrets)

## Common Use Cases

### 1. Chat Interface

```python
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("What's your question?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_ai_response(prompt)
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
```

### 2. File Upload & Processing

```python
uploaded_files = st.file_uploader(
    "Upload PDFs", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.processed_documents:
            with st.spinner(f"Processing {file.name}..."):
                content = process_pdf(file)
                add_to_vectorstore(content)
                st.session_state.processed_documents.add(file.name)
    
    st.success(f"✅ Processed {len(uploaded_files)} files")
```

### 3. Dashboard with Metrics

```python
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Revenue", "$45.2K", "+12%")
with col2:
    st.metric("Users", "1,234", "+5%")
with col3:
    st.metric("Conversion", "3.2%", "-0.1%")
with col4:
    st.metric("Churn", "2.1%", "-0.5%")

# Charts
st.plotly_chart(revenue_chart, use_container_width=True)
st.dataframe(transactions, use_container_width=True)
```

### 4. Data Display

```python
# Display DataFrame
st.dataframe(df, use_container_width=True)

# Interactive data editor
edited_df = st.data_editor(df, num_rows="dynamic")

# Static table
st.table(df.head(10))

# JSON
st.json(data_dict)

# Code block
st.code("""
def hello():
    print("Hello, World!")
""", language="python")
```

## Deployment Patterns

### 1. Requirements.txt

```txt
# Pin exact versions for production
streamlit==1.52.0
pandas==2.1.3
numpy==1.26.2
plotly==5.18.0

# Minimum version for development
requests>=2.31.0
```

### 2. Dockerfile

```dockerfile
FROM python:3.9-slim

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 -ms /bin/bash appuser

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

USER appuser
WORKDIR /home/appuser

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 3. Docker Build & Run

```bash
# Build
docker build -t my-streamlit-app .

# Run
docker run -p 8501:8501 my-streamlit-app
```

## Custom Theming (CSS Injection)

**Method used in PrelimStruct v3-5:**

```python
def apply_custom_theme():
    """Apply Gemini-style dark theme using CSS injection"""
    custom_css = """
    <style>
        /* Main background */
        .stApp {
            background-color: #131314;
        }
        
        /* Text color */
        .stMarkdown, .stText {
            color: #E8EAED;
        }
        
        /* Accent colors */
        .stButton>button {
            background-color: #8ab4f8;
            color: #131314;
        }
        
        /* Status badges */
        .status-pass {
            background-color: #34a853;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# Apply at app start
apply_custom_theme()
```

## Popular Component Libraries

Install with `pip install <package>`:

1. **pygwalker** (15.6K ⭐) - Tableau-style UI for dataframes
2. **streamlit-aggrid** (1.3K ⭐) - Advanced data grids
3. **streamlit-webrtc** (1.7K ⭐) - Audio/video streaming
4. **streamlit-folium** (571 ⭐) - Interactive maps
5. **streamlit-extras** (939 ⭐) - UI enhancements (cards, badges, etc.)
6. **st-pages** (525 ⭐) - Enhanced page navigation

**Component Hub**: https://streamlit.io/components

## Troubleshooting

### Widgets Resetting on Interaction

**Cause**: Not using session state

**Solution**: Store values in `st.session_state`

```python
# ❌ DON'T
count = 0
if st.button("Add"):
    count += 1

# ✅ DO
if 'count' not in st.session_state:
    st.session_state.count = 0
if st.button("Add"):
    st.session_state.count += 1
```

### Duplicate Widget Key Error

**Cause**: Same key used for multiple widgets

**Solution**: Use unique keys, especially in loops

```python
# ❌ DON'T
for i in range(3):
    st.text_input("Value")  # All have same implicit key

# ✅ DO
for i in range(3):
    st.text_input(f"Value {i}", key=f"input_{i}")
```

### Slow Performance

**Solutions:**
1. Use caching: `@st.cache_data` for data, `@st.cache_resource` for connections
2. Use forms for multiple inputs
3. Implement pagination for large datasets
4. Use `st.empty()` containers instead of clearing entire page

### Session State Not Persisting

**Cause**: Trying to store non-serializable objects

**Solution**: Only store serializable data (dicts, lists, primitives)

```python
# ❌ DON'T
st.session_state.db_connection = create_connection()  # Connection object

# ✅ DO
# Use @st.cache_resource for connections
@st.cache_resource
def get_connection():
    return create_connection()
```

## DOs and DON'Ts

### ✅ DO:
- Initialize session state at app start
- Use `@st.cache_data` for data operations
- Use `@st.cache_resource` for connections/models
- Call `st.set_page_config()` first in script
- Use forms for multi-field inputs
- Structure multipage apps with `pages/` directory
- Store secrets in `.streamlit/secrets.toml` (gitignored)
- Use unique keys for widgets in loops
- Separate UI and business logic
- Add spinners for long operations

### ❌ DON'T:
- Call `st.set_page_config()` after other commands
- Use global variables for state (use session_state)
- Cache database connections with `@st.cache_data` (use `@st.cache_resource`)
- Commit `secrets.toml` to git
- Create widgets in loops without unique keys
- Forget to handle exceptions in callbacks

## Resources

- **Official Docs**: https://docs.streamlit.io
- **API Reference**: https://docs.streamlit.io/develop/api-reference
- **Community Forum**: https://discuss.streamlit.io
- **Component Gallery**: https://streamlit.io/components
- **Cheat Sheet**: https://docs.streamlit.io/develop/quick-reference/cheat-sheet
