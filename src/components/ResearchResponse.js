import FeedbackForm from './FeedbackForm';

// Inside your response component
return (
  <div>
    {/* Your existing response display */}
    <div className="research-analysis">
      {/* ... your response content ... */}
    </div>
    
    {/* Add feedback form below the response */}
    <FeedbackForm 
      userQuery={currentQuery}
      aiResponse={response}
      paperIds={papers.map(p => p.id)}
    />
  </div>
); 