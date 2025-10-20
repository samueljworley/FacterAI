import React, { useState } from 'react';
import { Slider, TextField, Checkbox, Button, Box, Select, MenuItem } from '@mui/material';

const FeedbackForm = ({ userQuery, aiResponse, paperIds }) => {
  const [feedback, setFeedback] = useState({
    helpfulness: 3,
    clarity: 3,
    accuracy: 3,
    comment: '',
    quality: 'good',
    suggested_response: '',
    tags: [],
    revised_metrics: {
      clarity: 3,
      interpretation: 3,
      relevance: 3,
      depth: 3,
      citations_quality: 3,
      reasoning: 3
    },
    question_type: 'Research'
  });

  const [isBadResponse, setIsBadResponse] = useState(false);

  const handleMetricChange = (metric, value) => {
    setFeedback(prev => ({
      ...prev,
      revised_metrics: {
        ...prev.revised_metrics,
        [metric]: value
      }
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Update quality based on checkbox
    const quality = isBadResponse ? 'poor' : 'good';
    
    try {
      const response = await fetch('/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_query: userQuery,
          ai_response: aiResponse,
          paper_ids: paperIds,
          feedback: {
            ...feedback,
            quality,
            tags: generateTags()
          }
        }),
      });

      if (response.ok) {
        alert('Thank you for your feedback!');
        // Reset form
        setFeedback({
          helpfulness: 3,
          clarity: 3,
          accuracy: 3,
          comment: '',
          quality: 'good',
          suggested_response: '',
          tags: [],
          revised_metrics: {
            clarity: 3,
            interpretation: 3,
            relevance: 3,
            depth: 3,
            citations_quality: 3,
            reasoning: 3
          },
          question_type: 'Research'
        });
        setIsBadResponse(false);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const generateTags = () => {
    const tags = [];
    if (feedback.helpfulness > 4) tags.push('helpful');
    if (feedback.clarity > 4) tags.push('clear');
    if (feedback.accuracy > 4) tags.push('accurate');
    if (isBadResponse) tags.push('needs_improvement');
    return tags;
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3, p: 2, border: '1px solid #ddd', borderRadius: 2 }}>
      <h3>Original Response Feedback</h3>
      
      <Box sx={{ mb: 2 }}>
        <label>Helpfulness</label>
        <Slider
          value={feedback.helpfulness}
          onChange={(e, value) => setFeedback(prev => ({ ...prev, helpfulness: value }))}
          min={1}
          max={5}
          marks
          step={1}
        />
      </Box>

      <Box sx={{ mb: 2 }}>
        <label>Clarity</label>
        <Slider
          value={feedback.clarity}
          onChange={(e, value) => setFeedback(prev => ({ ...prev, clarity: value }))}
          min={1}
          max={5}
          marks
          step={1}
        />
      </Box>

      <Box sx={{ mb: 2 }}>
        <label>Accuracy</label>
        <Slider
          value={feedback.accuracy}
          onChange={(e, value) => setFeedback(prev => ({ ...prev, accuracy: value }))}
          min={1}
          max={5}
          marks
          step={1}
        />
      </Box>

      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          multiline
          rows={2}
          label="Comments (optional)"
          value={feedback.comment}
          onChange={(e) => setFeedback(prev => ({ ...prev, comment: e.target.value }))}
        />
      </Box>

      <Box sx={{ mb: 2 }}>
        <Checkbox
          checked={isBadResponse}
          onChange={(e) => setIsBadResponse(e.target.checked)}
        />
        <label>Flag this as a poor response</label>
      </Box>

      {isBadResponse && (
        <Box sx={{ mb: 2 }}>
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Suggest a better response"
            value={feedback.suggested_response}
            onChange={(e) => setFeedback(prev => ({ ...prev, suggested_response: e.target.value }))}
          />
        </Box>
      )}

      <h3>Revised Response Feedback</h3>
      {Object.entries(feedback.revised_metrics).map(([metric, value]) => (
        <Box key={metric} sx={{ mb: 2 }}>
          <label>{metric.replace('_', ' ').toUpperCase()}</label>
          <Slider
            value={value}
            onChange={(e, val) => handleMetricChange(metric, val)}
            min={1}
            max={5}
            marks
            step={1}
          />
        </Box>
      ))}

      <Box sx={{ mb: 2 }}>
        <label>Question Type</label>
        <Select
          fullWidth
          value={feedback.question_type}
          onChange={(e) => setFeedback(prev => ({ ...prev, question_type: e.target.value }))}
        >
          <MenuItem value="Research">Research</MenuItem>
          <MenuItem value="Math/Physics">Math/Physics</MenuItem>
          <MenuItem value="Concept">Concept</MenuItem>
          <MenuItem value="Coding">Coding</MenuItem>
        </Select>
      </Box>

      <Button variant="contained" type="submit" sx={{ mt: 2 }}>
        Submit Feedback
      </Button>
    </Box>
  );
};

export default FeedbackForm; 