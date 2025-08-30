# Summary Section Removal Plan

## Overview
This document outlines the changes needed to remove summary sections from responses in the chatbot system. The summary sections include:
- "**Summary:**" 
- "**Detailed Breakdown:**"
- "**Insights:**"
- "**Key Insights:**"
- "**Recommendations:**"
- "**Best Performance Analysis**"

## Files to Modify

### 1. rag_chatbot.py
**Location**: `rag_chatbot.py`

**Changes needed**:
- Add a helper function to strip summary sections from responses
- Modify the `format_best_performance_response` function to remove summary sections

**Specific locations**:
- Lines 115-143: The `format_best_performance_response` function contains summary sections
- Need to strip the following patterns:
  - "** Best Performance Analysis **"
  - "** Key Insights:**"
  - "** Recommendations:**"

### 2. flask_server.py  
**Location**: `flask_server.py`

**Changes needed**:
- Add a helper function to strip summary sections from responses
- Modify response handling to strip summary sections before returning

**Specific locations**:
- Lines 567-569: The validation endpoint checks for summary sections but doesn't strip them
- The main response handling in `send_message` function

## Implementation Approach

### Step 1: Add Helper Function
Add a function to strip summary sections from text:
```python
def strip_summary_sections(response_text):
    """
    Remove summary sections from response text.
    Removes patterns like "**Summary:**", "**Key Insights:**", etc.
    """
    if not isinstance(response_text, str):
        return response_text
        
    # Remove common summary section headers
    import re
    patterns_to_remove = [
        r'\*\* Best Performance Analysis \*\*',
        r'\*\* Key Insights:\*\*',
        r'\*\* Recommendations:\*\*',
        r'\*\*Summary:\*\*',
        r'\*\*Detailed Breakdown:\*\*',
        r'\*\*Insights:\*\*'
    ]
    
    result = response_text
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    return result.strip()
```

### Step 2: Modify Response Generation
In `rag_chatbot.py`, modify the `format_best_performance_response` function to not include summary sections, or use the helper function to strip them.

### Step 3: Apply to Final Responses
Ensure that the final response returned by the chatbot strips these sections.

## Testing Approach
1. Test the helper function with various response formats
2. Test integration with existing chatbot flows
3. Verify that actual functionality isn't impacted