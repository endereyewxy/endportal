## Database

### Table `blog`

| Field name | Type | Description | Remarks |
|:---:|:---:|-----|-----|
| publish_date | Date | The date when this blog is published | Not necessarily the same as when it is uploaded |
| publish_desc | Char(max_length=64) | A brief introduction about publishing |  |
| content_name | Char(max_length=64) | This blog's title |  |
| content_type | Char(max_length=16) | What kind of blog is this |  |
| content_imgs | Text | Images used by this blog | Filenames under static directory, separated by commas |
| content_tags | Text | Tags attached to this blog | Separated by commas |
| content_desc | Text | Introduction to this blog |  |
| content_text | Text | Content of this blog |  |
