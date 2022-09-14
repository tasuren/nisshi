# nisshi (**Beta**)
A simple and easy-to-understand static site generator.

You can install beta version by running this command:  
`pip install git+https://github.com/tasuren/nisshi`

## Examples
My [website](https://github.com/tasuren/website) and [portfolio](https://github.com/tasuren/portfolio) are made by nisshi.  
These website are built on github workflows.

## Quick start
nisshi use tempylate for template engine.  
So you should see that how to use [tempylate](https://github.com/tasuren/tempylate) for understanding nisshi.  
### Must know
`self` on tempylate is showing file.  
But on `nisshi`, it shows page.  
Markdown of page will be rendered and set to `self.content`.  
If you want set attribute to `self`, you should set it to `self.ctx`.
### Set up
Install nisshi first. (Installation command is above.)  
And make directories like the following:

```python
inputs # Put markdown documents here.
layouts # Put base html here. (Default is `layout.html`.)
includes # Put files to be copied into output directory here.
```
Make layout file `layout.html`.  
It will be used as a template for generate pages.  
In `layout.html`, embed the following block (`^^ here is block's content ^^`).  
They will be replaced at build time.  

```markdown
Title: `self.ctx.title`
Content of head element: `self.ctx.head`
Place to put the markdown made into HTML: `self.content`
```

Finally, you can build markdown by running `nisshi build`.  
Also, if you want to build realtime and serve files, you can use `nisshi serve`.
### Use
Just write markdown and put file into `inputs` directory.  
Also, you can set title by `^^ self.ctx.title = "..." ^^`.

### Extra
You can set an attribute on `self` to bring a value to `layout.html`.  

```python
^^
# e.g. `layout.html` will convert the following into string and be embeded.
self.ctx.last_updated = 1663161341.953884
^^
```

## License
MIT License